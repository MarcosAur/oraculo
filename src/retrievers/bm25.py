from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Plus

from .base import BaseRetriever


DEFAULT_CHUNKS_PATH = Path("data/bases/documentos/chunks.jsonl")
_WORD_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


class BM25Retriever(BaseRetriever):
    """Lexical retriever over chunks produced by the PDF ingestion pipeline."""

    def __init__(self, chunks: list[dict[str, Any]]):
        self.chunks = chunks
        self.corpus_tokens = [self._tokenize(chunk["text"]) for chunk in chunks]
        self.corpus_token_sets = [set(tokens) for tokens in self.corpus_tokens]
        self.bm25 = BM25Plus(self.corpus_tokens) if self.corpus_tokens else None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return _WORD_PATTERN.findall(text.casefold())

    @classmethod
    def from_jsonl(cls, chunks_path: str | Path = DEFAULT_CHUNKS_PATH) -> "BM25Retriever":
        path = Path(chunks_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"Knowledge base chunks not found at {path}. "
                "Run the PDF ingestion pipeline first."
            )

        chunks: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL in {path} at line {line_number}: {exc}"
                    ) from exc
                if not isinstance(chunk, dict) or not isinstance(chunk.get("text"), str):
                    raise ValueError(
                        f"Invalid chunk in {path} at line {line_number}: "
                        "a text field is required."
                    )
                chunks.append(chunk)
        return cls(chunks)

    def retrieve(
        self, query: str, top_k: int = 3, **kwargs: Any
    ) -> list[dict[str, Any]]:
        if self.bm25 is None or top_k <= 0:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_token_set = set(query_tokens)
        matching_indexes = [
            index
            for index, token_set in enumerate(self.corpus_token_sets)
            if token_set & query_token_set
        ]
        if not matching_indexes:
            return []

        scores = self.bm25.get_scores(query_tokens)
        scored_chunks: list[dict[str, Any]] = []
        for index in matching_indexes:
            chunk = self.chunks[index].copy()
            chunk["score"] = float(scores[index])
            scored_chunks.append(chunk)

        scored_chunks.sort(key=lambda item: item["score"], reverse=True)
        return scored_chunks[:top_k]
