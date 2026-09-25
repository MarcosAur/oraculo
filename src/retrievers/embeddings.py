from __future__ import annotations

from typing import Protocol, Sequence


DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
# Carregar o modelo leva segundos; a API cria um pipeline por requisição.
_MODEL_CACHE: dict[tuple[str, str | None], object] = {}


class Embedder(Protocol):
    """Converts texts into normalized dense vectors."""

    model_name: str

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Embeds texts with a sentence-transformers model loaded on first use.

    Modelos da família E5 foram treinados com os prefixos "query: " e
    "passage: "; eles são aplicados automaticamente quando o nome contém "e5".
    """

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        device: str | None = None,
        batch_size: int = 32,
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        uses_e5_prefixes = "e5" in model_name.casefold()
        self._query_prefix = "query: " if uses_e5_prefixes else ""
        self._passage_prefix = "passage: " if uses_e5_prefixes else ""

    @property
    def model(self):
        if self._model is None:
            key = (self.model_name, self.device)
            if key not in _MODEL_CACHE:
                from sentence_transformers import SentenceTransformer

                _MODEL_CACHE[key] = SentenceTransformer(
                    self.model_name, device=self.device
                )
            self._model = _MODEL_CACHE[key]
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode([self._passage_prefix + text for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._encode([self._query_prefix + text])[0]
