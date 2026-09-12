from __future__ import annotations

from pathlib import Path

from src.llm import LLMProvider
from src.retrievers.bm25 import BM25Retriever, DEFAULT_CHUNKS_PATH


class QAPipeline:
    """Retrieves ingested PDF chunks with BM25 and answers with an LLM."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        chunks_path: str | Path = DEFAULT_CHUNKS_PATH,
        db_session = None,
    ):
        self.chunks_path = Path(chunks_path)
        self.llm_provider = llm_provider
        if db_session is not None:
            self.retriever = BM25Retriever.from_jsonl_filtered(self.chunks_path, db_session)
        else:
            self.retriever = BM25Retriever.from_jsonl(self.chunks_path)
        self.chunks = self.retriever.chunks

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
