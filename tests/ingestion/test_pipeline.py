import json
from pathlib import Path

from src.ingestion.config import IngestionConfig
from src.ingestion.extractors import PAGE_BREAK_MARKER
from src.ingestion.models import ExtractionResult, SourceDocument
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.sources import DirectoryPdfSource


class FakeExtractor:
    def __init__(self):
        self.calls = 0

    def extract(self, source: SourceDocument, output_dir: Path) -> ExtractionResult:
        self.calls += 1
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "assets").mkdir()
        (output_dir / "assets" / "image-001.png").write_bytes(b"fake-image")
        (output_dir / "document.raw.md").write_text(
            f"# {source.file_name}\n\nPrimeira página.\n\n"
            f"{PAGE_BREAK_MARKER}\n\n## Dados\n\nSegunda página com tabela.\n\n"
            "| Campo | Valor |\n| --- | --- |\n| A | B |\n",
            encoding="utf-8",
        )
        return ExtractionResult(
            page_count=2,
            extraction_method="fake",
            status="success",
        )


def make_config(input_dir: Path, output_dir: Path) -> IngestionConfig:
    return IngestionConfig.from_mapping(
        {
            "source": {"input_dir": str(input_dir)},
            "output": {"root_dir": str(output_dir), "base_name": "knowledge"},
            "chunking": {
                "chunk_size": 80,
                "chunk_overlap": 10,
                "minimum_chunk_size": 0,
            },
        }
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_source_finds_nested_pdfs_case_insensitively(tmp_path: Path):
    (tmp_path / "nested").mkdir()
    (tmp_path / "a.PDF").write_bytes(b"a")
    (tmp_path / "nested" / "b.pdf").write_bytes(b"b")
    (tmp_path / "ignored.txt").write_text("ignored", encoding="utf-8")
    discovered = DirectoryPdfSource(tmp_path).discover()
    assert [item.relative_path for item in discovered] == ["a.PDF", "nested/b.pdf"]


def test_pipeline_is_incremental_and_replaces_modified_document(tmp_path: Path):
    input_dir = tmp_path / "pdfs"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    pdf = input_dir / "manual.pdf"
    pdf.write_bytes(b"version-one")
    config = make_config(input_dir, output_dir)
    extractor = FakeExtractor()

    first = IngestionPipeline(config, extractor=extractor).run()
    second = IngestionPipeline(config, extractor=extractor).run()
    assert first.processed == 1
    assert first.active_documents == 1
    assert second.processed == 0
    assert second.skipped == 1
    assert extractor.calls == 1

    base_dir = output_dir / "knowledge"
    first_document = read_jsonl(base_dir / "documents.jsonl")[0]
    assert (base_dir / first_document["markdown_path"]).is_file()
    assert (base_dir / first_document["assets_dir"] / "image-001.png").is_file()

    pdf.write_bytes(b"version-two")
    third = IngestionPipeline(config, extractor=extractor).run()
    documents = read_jsonl(base_dir / "documents.jsonl")
    chunks = read_jsonl(base_dir / "chunks.jsonl")
    assert third.processed == 1
    assert third.active_documents == 1
    assert extractor.calls == 2
    assert len(documents) == 1
    assert documents[0]["document_id"] != first_document["document_id"]
    assert not (base_dir / "documents" / first_document["document_id"]).exists()
    assert {chunk["document_id"] for chunk in chunks} == {documents[0]["document_id"]}


def test_failed_update_keeps_previous_valid_version(tmp_path: Path):
    input_dir = tmp_path / "pdfs"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    pdf = input_dir / "manual.pdf"
    pdf.write_bytes(b"valid")
    config = make_config(input_dir, output_dir)
    IngestionPipeline(config, extractor=FakeExtractor()).run()

    class BrokenExtractor:
        def extract(self, source: SourceDocument, output_dir: Path) -> ExtractionResult:
            raise RuntimeError("broken document")

    pdf.write_bytes(b"changed-but-invalid")
    summary = IngestionPipeline(config, extractor=BrokenExtractor()).run()
    base_dir = output_dir / "knowledge"
    documents = read_jsonl(base_dir / "documents.jsonl")
    failures = read_jsonl(base_dir / "failures.jsonl")
    assert summary.failed == 1
    assert summary.active_documents == 1
    assert len(documents) == 1
    assert failures[0]["message"] == "broken document"
