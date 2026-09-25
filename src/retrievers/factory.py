from __future__ import annotations

from pathlib import Path

from .base import BaseRetriever
from .bm25 import BM25Retriever, DEFAULT_CHUNKS_PATH
from .embeddings import DEFAULT_EMBEDDING_MODEL
from .hybrid import HybridRetriever
from .vector import VectorRetriever


RETRIEVER_MODES = ("bm25", "vector", "hybrid")


def build_retriever(
    mode: str = "bm25",
    chunks_path: str | Path = DEFAULT_CHUNKS_PATH,
    *,
    db_session=None,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> BaseRetriever:
    """Creates the retriever for one ingestion base.

    O índice vetorial fica em ``<pasta do chunks.jsonl>/chroma``.
    """
    if mode not in RETRIEVER_MODES:
        raise ValueError(
            f"Retriever '{mode}' não suportado. Use: {', '.join(RETRIEVER_MODES)}."
        )

    chunks_path = Path(chunks_path)
    vector = None
    if mode in ("vector", "hybrid"):
        vector = VectorRetriever.from_base(
            chunks_path.parent,
            embedding_model=embedding_model,
            db_session=db_session,
        )
        if mode == "vector":
            return vector

    if db_session is not None:
        bm25 = BM25Retriever.from_jsonl_filtered(chunks_path, db_session)
    else:
        bm25 = BM25Retriever.from_jsonl(chunks_path)
    if mode == "bm25":
        return bm25
    return HybridRetriever([bm25, vector])
