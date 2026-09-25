import hashlib
import json
import math
import re
from pathlib import Path

import pytest

from src.retrievers import BM25Retriever, HybridRetriever, VectorRetriever
from src.retrievers.vector import ChromaVectorStore


class FakeEmbedder:
    """Deterministic bag-of-words embedder: shared words -> similar vectors."""

    def __init__(self, model_name: str = "fake-model", dimensions: int = 64):
        self.model_name = model_name
        self.dimensions = dimensions
        self.embedded: list[str] = []

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in re.findall(r"\w+", text.casefold()):
            bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimensions
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts):
        self.embedded.extend(texts)
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        return self._vector(text)


CHUNKS = [
    {
        "chunk_id": "manual-1",
        "document_id": "manual",
        "chunk_index": 1,
        "source_path": "manual.pdf",
        "page_start": 1,
        "page_end": 2,
        "section_path": ["Instalação"],
        "text": "Execute flutter pub get para instalar as dependências.",
    },
    {
        "chunk_id": "arquitetura-1",
        "document_id": "arquitetura",
        "chunk_index": 1,
        "source_path": "arquitetura.pdf",
        "page_start": 4,
        "page_end": 4,
        "section_path": [],
        "text": "O aplicativo trabalha offline e sincroniza com a API.",
    },
]


def make_store(tmp_path: Path, embedder=None) -> ChromaVectorStore:
    return ChromaVectorStore(tmp_path / "chroma", embedder or FakeEmbedder())


def test_sync_is_incremental_and_removes_stale_chunks(tmp_path: Path):
    embedder = FakeEmbedder()
    store = make_store(tmp_path, embedder)

    first = store.sync(CHUNKS)
    assert (first.added, first.removed, first.total) == (2, 0, 2)
    assert embedder.embedded[0].startswith("Instalação\n")

    second = store.sync(CHUNKS)
    assert (second.added, second.removed, second.unchanged) == (0, 0, 2)
    assert len(embedder.embedded) == 2

    third = store.sync(CHUNKS[:1])
    assert (third.added, third.removed, third.total) == (0, 1, 1)
    assert store.indexed_ids() == {"manual-1"}


def test_search_returns_metadata_and_respects_document_filter(tmp_path: Path):
    store = make_store(tmp_path)
    store.sync(CHUNKS)

    results = VectorRetriever(store).retrieve("sincroniza offline com a API", top_k=2)
    assert results[0]["chunk_id"] == "arquitetura-1"
    assert results[0]["source_path"] == "arquitetura.pdf"
    assert results[0]["page_start"] == 4
    assert results[0]["section_path"] == []
    assert results[0]["score"] > results[1]["score"]

    filtered = VectorRetriever(store, document_ids={"manual"}).retrieve(
        "sincroniza offline com a API", top_k=2
    )
    assert [chunk["chunk_id"] for chunk in filtered] == ["manual-1"]
    assert VectorRetriever(store, document_ids=set()).retrieve("API") == []


def test_index_persists_and_is_rebuilt_when_model_changes(tmp_path: Path):
    make_store(tmp_path).sync(CHUNKS)
    assert make_store(tmp_path).count() == 2

    other_model = make_store(tmp_path, FakeEmbedder(model_name="other-model"))
    assert other_model.count() == 0
    summary = other_model.sync(CHUNKS)
    assert summary.rebuilt and summary.added == 2


def test_from_base_requires_an_index(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="index_vectors"):
        VectorRetriever.from_base(tmp_path, embedder=FakeEmbedder())


def test_hybrid_fuses_lexical_and_vector_rankings(tmp_path: Path):
    store = make_store(tmp_path)
    store.sync(CHUNKS)
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        "".join(json.dumps(chunk) + "\n" for chunk in CHUNKS), encoding="utf-8"
    )
    hybrid = HybridRetriever(
        [BM25Retriever.from_jsonl(chunks_path), VectorRetriever(store)]
    )

    results = hybrid.retrieve("instalar dependências flutter", top_k=2)

    assert results[0]["chunk_id"] == "manual-1"
    assert set(results[0]["scores"]) == {"BM25Retriever", "VectorRetriever"}
    assert len({chunk["chunk_id"] for chunk in results}) == len(results)
