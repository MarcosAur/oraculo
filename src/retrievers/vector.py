from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .base import BaseRetriever
from .embeddings import DEFAULT_EMBEDDING_MODEL, Embedder, SentenceTransformerEmbedder


DEFAULT_BASE_DIR = Path("data/bases/documentos")
DEFAULT_COLLECTION_NAME = "chunks"
CHROMA_DIR_NAME = "chroma"
_ADD_BATCH_SIZE = 64
_DELETE_BATCH_SIZE = 500


@dataclass(frozen=True)
class VectorSyncSummary:
    added: int
    removed: int
    unchanged: int
    total: int
    rebuilt: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": self.added,
            "removed": self.removed,
            "unchanged": self.unchanged,
            "total": self.total,
            "rebuilt": self.rebuilt,
        }


def _embedding_input(chunk: dict[str, Any]) -> str:
    """Text sent to the embedding model: section headings give the chunk context."""
    section = " > ".join(chunk.get("section_path") or [])
    return f"{section}\n{chunk['text']}" if section else chunk["text"]


def _chunk_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk.get("document_id") or "",
        "chunk_index": int(chunk.get("chunk_index") or 0),
        "source_path": chunk.get("source_path") or "",
        "section_path": json.dumps(chunk.get("section_path") or [], ensure_ascii=False),
    }
    for key in ("page_start", "page_end", "token_count"):
        if chunk.get(key) is not None:
            metadata[key] = int(chunk[key])
    return metadata


def _chunk_from_result(text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    chunk = dict(metadata)
    chunk["section_path"] = json.loads(metadata.get("section_path") or "[]")
    chunk["text"] = text
    return chunk


def _batched(items: list, size: int) -> Iterable[list]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class ChromaVectorStore:
    """Persistent ChromaDB collection mirroring the chunks of one ingestion base.

    O ``chunk_id`` já é um hash do documento, da posição e do texto; por isso a
    sincronização só precisa comparar IDs: chunks novos são vetorizados e
    chunks que sumiram do ``chunks.jsonl`` são removidos.
    """

    def __init__(
        self,
        persist_dir: str | Path,
        embedder: Embedder,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ):
        import chromadb
        from chromadb.config import Settings

        self.persist_dir = Path(persist_dir)
        self.embedder = embedder
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self._open_collection()
        self._rebuilt = False
        indexed_model = (self.collection.metadata or {}).get("embedding_model")
        if indexed_model and indexed_model != embedder.model_name:
            # Vetores de modelos diferentes não são comparáveis: recria o índice.
            self.client.delete_collection(collection_name)
            self.collection = self._open_collection()
            self._rebuilt = True

    @classmethod
    def for_base(
        cls,
        base_dir: str | Path = DEFAULT_BASE_DIR,
        embedder: Embedder | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> "ChromaVectorStore":
        return cls(
            Path(base_dir) / CHROMA_DIR_NAME,
            embedder or SentenceTransformerEmbedder(),
            collection_name,
        )

    def _open_collection(self):
        return self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": self.embedder.model_name,
            },
            embedding_function=None,
        )

    def count(self) -> int:
        return self.collection.count()

    def indexed_ids(self) -> set[str]:
        return set(self.collection.get(include=[])["ids"])

    def sync(
        self,
        chunks: list[dict[str, Any]],
        progress: Callable[[str], None] | None = None,
    ) -> VectorSyncSummary:
        progress = progress or (lambda _message: None)
        wanted = {chunk["chunk_id"]: chunk for chunk in chunks if chunk.get("chunk_id")}
        existing = self.indexed_ids()

        to_remove = sorted(existing - wanted.keys())
        to_add = [chunk for chunk_id, chunk in wanted.items() if chunk_id not in existing]

        for batch in _batched(to_remove, _DELETE_BATCH_SIZE):
            self.collection.delete(ids=batch)

        for position, batch in enumerate(_batched(to_add, _ADD_BATCH_SIZE), start=1):
            progress(
                f"Embedding chunks {min(position * _ADD_BATCH_SIZE, len(to_add))}"
                f"/{len(to_add)}"
            )
            self.collection.add(
                ids=[chunk["chunk_id"] for chunk in batch],
                embeddings=self.embedder.embed_documents(
                    [_embedding_input(chunk) for chunk in batch]
                ),
                documents=[chunk["text"] for chunk in batch],
                metadatas=[_chunk_metadata(chunk) for chunk in batch],
            )

        return VectorSyncSummary(
            added=len(to_add),
            removed=len(to_remove),
            unchanged=len(existing & wanted.keys()),
            total=self.count(),
            rebuilt=self._rebuilt,
        )

    def search(
        self,
        query: str,
        top_k: int,
        document_ids: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        total = self.count()
        if top_k <= 0 or total == 0 or not query.strip():
            return []

        where = None
        if document_ids is not None:
            allowed = sorted(set(document_ids))
            if not allowed:
                return []
            where = {"document_id": {"$in": allowed}}

        result = self.collection.query(
            query_embeddings=[self.embedder.embed_query(query)],
            n_results=min(top_k, total),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for text, metadata, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            chunk = _chunk_from_result(text, metadata)
            # Distância de cosseno -> similaridade (1 = idêntico).
            chunk["score"] = 1.0 - float(distance)
            chunks.append(chunk)
        return chunks


class VectorRetriever(BaseRetriever):
    """Semantic retriever backed by the ChromaDB index of an ingestion base."""

    def __init__(
        self,
        store: ChromaVectorStore,
        document_ids: Iterable[str] | None = None,
        min_score: float | None = None,
    ):
        self.store = store
        self.document_ids = set(document_ids) if document_ids is not None else None
        self.min_score = min_score

    @classmethod
    def from_base(
        cls,
        base_dir: str | Path = DEFAULT_BASE_DIR,
        *,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        embedder: Embedder | None = None,
        db_session=None,
        min_score: float | None = None,
    ) -> "VectorRetriever":
        chroma_dir = Path(base_dir) / CHROMA_DIR_NAME
        if not chroma_dir.is_dir():
            raise FileNotFoundError(
                f"Vector index not found at {chroma_dir}. "
                "Run: python -m src.cli.index_vectors"
            )
        store = ChromaVectorStore(
            chroma_dir, embedder or SentenceTransformerEmbedder(embedding_model)
        )
        if store.count() == 0:
            raise FileNotFoundError(
                f"Vector index at {chroma_dir} is empty. "
                "Run: python -m src.cli.index_vectors"
            )

        document_ids = None
        if db_session is not None:
            from src.api.models.document import Document

            document_ids = {
                row[0]
                for row in db_session.query(Document.document_id)
                .filter(Document.deleted_at.is_(None))
                .all()
            }
        return cls(store, document_ids=document_ids, min_score=min_score)

    def retrieve(self, query: str, top_k: int = 3, **kwargs: Any) -> list[dict[str, Any]]:
        results = self.store.search(query, top_k, document_ids=self.document_ids)
        if self.min_score is not None:
            results = [chunk for chunk in results if chunk["score"] >= self.min_score]
        return results
