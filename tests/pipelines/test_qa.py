import json
from pathlib import Path

from src.pipelines import QAPipeline


class FakeProvider:
    def __init__(self):
        self.prompt = ""

    def generate(self, prompt: str, model: str, **kwargs) -> str:
        self.prompt = prompt
        return "Resposta baseada no manual.pdf."


def test_qa_uses_chunks_from_current_ingestion(tmp_path: Path):
    chunks_path = tmp_path / "chunks.jsonl"
    chunk = {
        "chunk_id": "chunk-1",
        "chunk_index": 1,
        "source_path": "manual.pdf",
        "page_start": 3,
        "page_end": 3,
        "text": "Use flutter run para executar o aplicativo.",
    }
    chunks_path.write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    provider = FakeProvider()

    result = QAPipeline(provider, chunks_path).answer(
        "Como executar o aplicativo?", llm_model="fake"
    )

    assert result["sources"][0]["source_path"] == "manual.pdf"
    assert "flutter run" in provider.prompt
    assert "Fonte: manual.pdf" in provider.prompt


def test_qa_does_not_call_llm_when_nothing_matches(tmp_path: Path):
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        json.dumps({"text": "Manual do aplicativo", "source_path": "manual.pdf"})
        + "\n",
        encoding="utf-8",
    )
    provider = FakeProvider()

    result = QAPipeline(provider, chunks_path).answer(
        "astronomia quântica", llm_model="fake"
    )

    assert result["sources"] == []
    assert provider.prompt == ""
