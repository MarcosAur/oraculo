from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from .config import PaddleOcrConfig
from .models import ExtractionResult, SourceDocument


PAGE_BREAK_MARKER = "<!-- page-break -->"


class DocumentExtractor(Protocol):
    def extract(
        self, source: SourceDocument, output_dir: Path
    ) -> ExtractionResult: ...


class PaddleOcrPdfExtractor:
    """Extract PDF pages to Markdown using PaddleOCR."""

    def __init__(
        self,
        config: PaddleOcrConfig | None = None,
        *,
        engine: Any | None = None,
    ):
        self.config = config or PaddleOcrConfig()
        self._engine = engine

    def _build_engine(self) -> Any:
        try:
            import paddle
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Run: "
                "python -m pip install -r requirements.txt"
            ) from exc

        if (
            self.config.device.lower().startswith("gpu")
            and not paddle.device.is_compiled_with_cuda()
        ):
            raise RuntimeError(
                "GPU requested, but the installed PaddlePaddle has no CUDA "
                "support. Install paddlepaddle-gpu or use --device cpu."
            )

        return PaddleOCR(
            lang=self.config.language,
            device=self.config.device,
            # PaddlePaddle 3.3.x can fail while converting PIR attributes in
            # the oneDNN executor on CPU. Use the regular Paddle CPU backend
            # until that combination is fixed upstream.
            enable_mkldnn=False,
            use_doc_orientation_classify=(
                self.config.use_doc_orientation_classify
            ),
            use_doc_unwarping=self.config.use_doc_unwarping,
            use_textline_orientation=self.config.use_textline_orientation,
        )

    @property
    def engine(self) -> Any:
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    @staticmethod
    def _result_data(result: Any) -> Mapping[str, Any]:
        payload = getattr(result, "json", result)
        if callable(payload):
            payload = payload()
        if not isinstance(payload, Mapping):
            raise TypeError("PaddleOCR returned an unsupported result.")
        nested = payload.get("res")
        return nested if isinstance(nested, Mapping) else payload

    def _page_markdown(self, result: Any) -> tuple[str, list[str]]:
        data = self._result_data(result)
        texts = data.get("rec_texts", [])
        scores = data.get("rec_scores", [])
        if not isinstance(texts, Iterable) or isinstance(texts, (str, bytes)):
            raise TypeError("PaddleOCR result does not contain a valid rec_texts list.")

        text_items = list(texts)
        score_items = list(scores) if isinstance(scores, Iterable) else []
        accepted: list[str] = []
        warnings: list[str] = []
        for index, text in enumerate(text_items):
            value = str(text).strip()
            if not value:
                continue
            score = float(score_items[index]) if index < len(score_items) else 1.0
            if score >= self.config.minimum_confidence:
                accepted.append(value)
            else:
                warnings.append(
                    f"Discarded OCR line {index + 1} with confidence {score:.3f}."
                )
        return "\n\n".join(accepted), warnings

    def extract(
        self, source: SourceDocument, output_dir: Path
    ) -> ExtractionResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "assets").mkdir(exist_ok=True)

        pages: list[str] = []
        warnings: list[str] = []
        for result in self.engine.predict(input=source.path):
            markdown, page_warnings = self._page_markdown(result)
            pages.append(markdown)
            warnings.extend(page_warnings)

        if not pages:
            raise ValueError("PaddleOCR did not return any PDF pages.")

        raw_markdown = f"\n\n{PAGE_BREAK_MARKER}\n\n".join(pages).strip()
        if not raw_markdown:
            raise ValueError("PaddleOCR did not recognize any text in the PDF.")
        (output_dir / "document.raw.md").write_text(
            raw_markdown + "\n", encoding="utf-8"
        )

        return ExtractionResult(
            page_count=len(pages),
            extraction_method="paddleocr",
            status="success",
            languages=[self.config.language],
            warnings=warnings,
        )


class NativePdfExtractor:
    """Extract text from native (text-based) PDFs using PyMuPDF.

    Much faster than OCR since it reads the embedded text layer directly.
    Produces the same ``document.raw.md`` output format as
    :class:`PaddleOcrPdfExtractor` so both are interchangeable in the
    pipeline.
    """

    def extract(
        self, source: SourceDocument, output_dir: Path
    ) -> ExtractionResult:
        try:
            import pymupdf
        except ImportError:
            try:
                import fitz as pymupdf  # type: ignore[no-redef]
            except ImportError as exc:
                raise RuntimeError(
                    "PyMuPDF is required for native PDF extraction. "
                    "Run: pip install PyMuPDF"
                ) from exc

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "assets").mkdir(exist_ok=True)

        doc = pymupdf.open(source.path)
        pages: list[str] = []
        warnings: list[str] = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()
                if text:
                    pages.append(text)
                else:
                    pages.append("")
                    warnings.append(
                        f"Page {page_num + 1} yielded no extractable text."
                    )
        finally:
            doc.close()

        if not pages:
            raise ValueError("PyMuPDF did not find any pages in the PDF.")

        raw_markdown = f"\n\n{PAGE_BREAK_MARKER}\n\n".join(pages).strip()
        if not raw_markdown:
            raise ValueError(
                "PyMuPDF did not extract any text from the PDF."
            )
        (output_dir / "document.raw.md").write_text(
            raw_markdown + "\n", encoding="utf-8"
        )

        return ExtractionResult(
            page_count=len(pages),
            extraction_method="native_pymupdf",
            status="success",
            languages=[],
            warnings=warnings,
        )
