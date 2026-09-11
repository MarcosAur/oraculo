from pathlib import Path

import read_pdf as read_pdf_module


class FakeExtractor:
    def __init__(self, config):
        self.config = config

    def extract(self, source, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "document.raw.md").write_text(
            "Texto reconhecido.\n", encoding="utf-8"
        )

        class Result:
            page_count = 1
            warnings = []

        return Result()


def test_read_pdf_writes_txt_next_to_pdf(tmp_path: Path, monkeypatch):
    pdf = tmp_path / "documento.pdf"
    pdf.write_bytes(b"%PDF-fake")
    monkeypatch.setattr(read_pdf_module, "PaddleOcrPdfExtractor", FakeExtractor)

    output = read_pdf_module.read_pdf(pdf)

    assert output == tmp_path / "documento.txt"
    assert output.read_text(encoding="utf-8") == "Texto reconhecido.\n"
