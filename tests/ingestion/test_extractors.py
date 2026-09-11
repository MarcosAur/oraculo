from pathlib import Path

from src.ingestion.config import PaddleOcrConfig
from src.ingestion.extractors import PAGE_BREAK_MARKER, PaddleOcrPdfExtractor
from src.ingestion.models import SourceDocument


class FakeResult:
    def __init__(self, texts: list[str], scores: list[float]):
        self.json = {"res": {"rec_texts": texts, "rec_scores": scores}}


class FakePaddleOcr:
    def predict(self, *, input: str):
        assert input.endswith("manual.pdf")
        return [
            FakeResult(["Primeira linha", "Ruído"], [0.99, 0.2]),
            FakeResult(["Segunda página"], [0.95]),
        ]


def test_paddle_ocr_extractor_writes_paginated_markdown(tmp_path: Path):
    source = SourceDocument(
        path=str(tmp_path / "manual.pdf"),
        relative_path="manual.pdf",
        file_name="manual.pdf",
        size_bytes=10,
    )
    extractor = PaddleOcrPdfExtractor(
        PaddleOcrConfig(language="pt", minimum_confidence=0.5),
        engine=FakePaddleOcr(),
    )

    result = extractor.extract(source, tmp_path / "output")

    markdown = (tmp_path / "output" / "document.raw.md").read_text(
        encoding="utf-8"
    )
    assert markdown == (
        f"Primeira linha\n\n{PAGE_BREAK_MARKER}\n\nSegunda página\n"
    )
    assert result.page_count == 2
    assert result.extraction_method == "paddleocr"
    assert result.languages == ["pt"]
    assert len(result.warnings) == 1
