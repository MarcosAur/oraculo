from typing import List, Dict, Any
from .base import BaseRetriever
from rank_bm25 import BM25Okapi
import tiktoken

class BM25Retriever(BaseRetriever):
    """
    A concrete retriever that uses the BM25Okapi algorithm over tokenized text.
    Implements the BaseRetriever interface.
    """
    
    def __init__(self, chunks: List[Dict[str, Any]], model_name: str = "gpt-4.1"):
        """
        Initializes the BM25Retriever with a list of pre-tokenized chunks.
        
        Args:
            chunks: A list of dictionaries representing chunks. Each chunk must contain a "tokens" key.
            model_name: The model name to load the correct tiktoken encoding.
        """
        self.chunks = chunks
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
            
        # Extract the corpus tokens (list of lists of token IDs)
        corpus_tokens = [chunk["tokens"] for chunk in chunks]
        self.bm25 = BM25Okapi(corpus_tokens)

    def retrieve(self, query: str, top_k: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieves the top_k most similar chunks for the given raw text query.
        
        Args:
            query: The raw string query from the user.
            top_k: The number of relevant documents to return.
            
        Returns:
            A list of the top_k scoring chunks, containing a "score" key.
        """
        if not self.chunks:
            return []
            
        # Tokenize the query using the same encoding
        query_tokens = self.encoding.encode(query)
        
        # Calculate BM25 scores for each chunk
        scores = self.bm25.get_scores(query_tokens)
        
        scored_chunks = []
        for i, chunk in enumerate(self.chunks):
            chunk_copy = chunk.copy()
            chunk_copy["score"] = float(scores[i])
            scored_chunks.append(chunk_copy)
            
        # Sort by score in descending order
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)  
        
        # Filter chunks to only keep those with a score > 1.0
        filtered_chunks = [chunk for chunk in scored_chunks if chunk["score"] > 0.7]
        
        # If no chunks meet the threshold, return the fallback message
        if not filtered_chunks:
            return "Seja mais específico na pergunta"
            
        # Return the top_k results
        return filtered_chunks[:top_k]

