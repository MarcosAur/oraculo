from __future__ import annotations

from typing import Any

from .base import BaseRetriever


class HybridRetriever(BaseRetriever):
    """Combines lexical and semantic rankings with Reciprocal Rank Fusion.

    Os scores do BM25 e da similaridade de cosseno estão em escalas
    diferentes, então a fusão usa apenas a posição de cada chunk em cada
    ranking: score = soma de 1 / (k + posição).
    """

    def __init__(
        self,
        retrievers: list[BaseRetriever],
        *,
        rrf_k: int = 60,
        candidates_per_retriever: int = 20,
    ):
        self.retrievers = retrievers
        self.rrf_k = rrf_k
        self.candidates_per_retriever = candidates_per_retriever

    @staticmethod
    def _key(chunk: dict[str, Any]) -> str:
        return chunk.get("chunk_id") or chunk["text"]

    def retrieve(self, query: str, top_k: int = 3, **kwargs: Any) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []

        candidates = max(top_k, self.candidates_per_retriever)
        fused: dict[str, dict[str, Any]] = {}
        for retriever in self.retrievers:
            ranking = retriever.retrieve(query, top_k=candidates, **kwargs)
            for position, chunk in enumerate(ranking, start=1):
                key = self._key(chunk)
                entry = fused.setdefault(key, {**chunk, "score": 0.0, "scores": {}})
                entry["score"] += 1.0 / (self.rrf_k + position)
                entry["scores"][type(retriever).__name__] = chunk["score"]

        results = sorted(fused.values(), key=lambda item: item["score"], reverse=True)
        return results[:top_k]
