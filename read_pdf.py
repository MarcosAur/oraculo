from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from src.ingestion.config import PaddleOcrConfig
from src.ingestion.extractors import PaddleOcrPdfExtractor
from src.ingestion.models import SourceDocument


def read_pdf(
    pdf_path: str | Path,
    output_path: str | Path | None = None,
    *,
    language: str = "pt",
    device: str = "cpu",
    minimum_confidence: float = 0.5,
) -> Path:
    source_path = Path(pdf_path).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise ValueError(f"O arquivo informado não é um PDF: {source_path}")

    destination = (
        Path(output_path).expanduser().resolve()
        if output_path
        else source_path.with_suffix(".txt")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)

    source = SourceDocument(
        path=str(source_path),
        relative_path=source_path.name,
        file_name=source_path.name,
        size_bytes=source_path.stat().st_size,
    )
    config = PaddleOcrConfig(
        language=language,
        device=device,
        minimum_confidence=minimum_confidence,
    )

    with tempfile.TemporaryDirectory(prefix="oraculo-paddleocr-") as temp_dir:
        extraction_dir = Path(temp_dir)
        result = PaddleOcrPdfExtractor(config).extract(source, extraction_dir)
        shutil.copyfile(extraction_dir / "document.raw.md", destination)

    print(
        f"Texto extraído de {result.page_count} página(s) e salvo em: "
        f"{destination}"
    )
    if result.warnings:
        print(f"Avisos do OCR: {len(result.warnings)}")
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrai o texto de um PDF usando PaddleOCR."
    )
    parser.add_argument("pdf", help="Caminho do arquivo PDF.")
    parser.add_argument(
        "-o",
        "--output",
        help="Arquivo TXT de saída. O padrão é <nome-do-pdf>.txt.",
    )
    parser.add_argument(
        "--language",
        default="pt",
        help="Idioma do PaddleOCR (padrão: pt).",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Dispositivo do PaddleOCR, por exemplo cpu ou gpu:0 (padrão: cpu).",
    )
    parser.add_argument(
        "--minimum-confidence",
        type=float,
        default=0.5,
        help="Confiança mínima entre 0 e 1 (padrão: 0.5).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if not 0 <= args.minimum_confidence <= 1:
            raise ValueError("A confiança mínima deve estar entre 0 e 1.")
        read_pdf(
            args.pdf,
            args.output,
            language=args.language,
            device=args.device,
            minimum_confidence=args.minimum_confidence,
        )
    except (FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
        raise SystemExit(f"Erro: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
