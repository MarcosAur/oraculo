import json
from pathlib import Path

from src.retrievers import BM25Retriever


def write_chunks(path: Path) -> None:
    chunks = [
        {
            "chunk_id": "manual-1",
            "chunk_index": 1,
            "source_path": "manual.pdf",
            "page_start": 1,
            "page_end": 2,
            "text": "Execute flutter pub get para instalar as dependências.",
        },
        {
            "chunk_id": "arquitetura-1",
            "chunk_index": 1,
            "source_path": "arquitetura.pdf",
            "page_start": 1,
            "page_end": 1,
            "text": "O aplicativo trabalha offline e sincroniza com a API.",
        },
    ]
    path.write_text(
        "".join(json.dumps(chunk) + "\n" for chunk in chunks),
        encoding="utf-8",
    )


def test_retriever_loads_current_ingestion_jsonl(tmp_path: Path):
    chunks_path = tmp_path / "chunks.jsonl"
    write_chunks(chunks_path)

    results = BM25Retriever.from_jsonl(chunks_path).retrieve(
        "Como instalar as dependências com flutter?", top_k=2
    )

    assert results
    assert results[0]["source_path"] == "manual.pdf"
    assert results[0]["score"] > 0
    assert "tokens" not in results[0]


def test_retriever_returns_empty_list_when_terms_are_absent(tmp_path: Path):
    chunks_path = tmp_path / "chunks.jsonl"
    write_chunks(chunks_path)

    results = BM25Retriever.from_jsonl(chunks_path).retrieve("astronomia quântica")

    assert results == []
