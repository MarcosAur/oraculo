from __future__ import annotations

from pathlib import Path

from src.llm import LLMProvider
from src.retrievers.base import BaseRetriever
from src.retrievers.bm25 import DEFAULT_CHUNKS_PATH
from src.retrievers.embeddings import DEFAULT_EMBEDDING_MODEL
from src.retrievers.factory import build_retriever


class QAPipeline:
    """Retrieves ingested PDF chunks (BM25, vector or hybrid) and answers with an LLM."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        chunks_path: str | Path = DEFAULT_CHUNKS_PATH,
        db_session = None,
        retriever_mode: str = "bm25",
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        retriever: BaseRetriever | None = None,
    ):
        self.chunks_path = Path(chunks_path)
        self.llm_provider = llm_provider
        self.retriever = retriever or build_retriever(
            retriever_mode,
            self.chunks_path,
            db_session=db_session,
            embedding_model=embedding_model,
        )

    def answer(self, question: str, llm_model: str, top_k: int = 3) -> dict:
        relevant_chunks = self.retriever.retrieve(question, top_k=top_k)
        if not relevant_chunks:
            return {
                "question": question,
                "answer": "Não encontrei informações relacionadas na base de documentos.",
                "sources": [],
            }

        context_parts = []
        for chunk in relevant_chunks:
            source = chunk.get("source_path", "documento desconhecido")
            page_start = chunk.get("page_start", "?")
            page_end = chunk.get("page_end", "?")
            pages = f"páginas {page_start}-{page_end}"
            text = chunk["text"]
            context_parts.append(f"Fonte: {source} ({pages})\n{text}")
        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""Você responde perguntas usando exclusivamente o contexto recuperado dos documentos.
Se o contexto não contiver a resposta, informe claramente que a informação não foi encontrada.
Responda de forma direta e cite o nome do documento usado.

Contexto:
{context}

Pergunta:
{question}

Resposta:"""

        answer_text = self.llm_provider.generate(prompt, model=llm_model)
        return {
            "question": question,
            "answer": answer_text,
            "sources": relevant_chunks,
        }
