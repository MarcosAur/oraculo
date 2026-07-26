import json
import os
from retrievers import BM25Retriever
from llm import LLMProvider

class QAPipeline:
    """
    Pipeline responsible for loading stored chunks, retrieving relevant context
    using a retriever, constructing a prompt, and generating answers using an LLM.
    """
    
    def __init__(self, llm_provider: LLMProvider, chunks_path: str = "data/chunks_cache.json"):
        """
        Initializes the QA Pipeline.
        
        Args:
            llm_provider: Concrete implementation of LLMProvider.
            chunks_path: Path to the cached chunks JSON file.
        """
        self.chunks_path = chunks_path
        self.llm_provider = llm_provider
        
        if not os.path.exists(self.chunks_path):
            raise FileNotFoundError(
                f"Knowledge base chunks not found at {self.chunks_path}. "
                "Please run the ingestion pipeline first."
            )
            
        self.chunks = self._load_chunks()
        # Initialize retriever with the loaded chunks
        self.retriever = BM25Retriever(self.chunks)

    def _load_chunks(self) -> list:
        with open(self.chunks_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def answer(self, question: str, llm_model: str, top_k: int = 3) -> dict:
        """
        Retrieves context, formats RAG prompt, gets LLM response and returns a dictionary.
        
        Args:
            question: User's question text.
            llm_model: LLM model name to use.
            top_k: Number of retrieved chunks to include in the context.
            
        Returns:
            Dictionary containing: 'question', 'answer', and 'sources'.
        """
        # 1. Retrieve most relevant chunks
        relevant_chunks = self.retriever.retrieve(question, top_k=top_k)
        
        # If the retriever returned a message string instead of a list of chunks, bypass LLM
        if isinstance(relevant_chunks, str):
            return {
                "question": question,
                "answer": relevant_chunks,  # Returns "Seja mais específico na pergunta"
                "sources": []
            }
        
        # 2. Combine chunk texts into single context block
        context = "\n\n".join([chunk["text"] for chunk in relevant_chunks])

        
        # 3. Create RAG prompt
        prompt = f"""Você é um assistente virtual especialista no Edital do Concurso Público.
Responda à pergunta do usuário utilizando estritamente as informações fornecidas no contexto abaixo.
Se a resposta não puder ser encontrada ou deduzida a partir do contexto, diga de forma educada que não possui essa informação. Q
Responda de forma clara e simples em um texto curto de 2 parágrafos.


Contexto:
{context}

Pergunta:
{question}

Resposta:"""
        
        # 4. Invoke LLM provider
        answer_text = self.llm_provider.generate(prompt, model=llm_model)
        
        return {
            "question": question,
            "answer": answer_text,
            "sources": relevant_chunks
        }
