from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

class BM25OkapiRetriever:
    """
    A retriever wrapper around rank_bm25's BM25Okapi, 
    working directly with lists of token IDs (integers).
    """
    
    def __init__(self, corpus_tokens: List[List[int]]):
        """
        Initializes the retriever with corpus document token lists.
        
        Args:
            corpus_tokens: List of token lists for each document/chunk.
        """
        # rank_bm25's BM25Okapi expects a list of lists of tokens
        self.bm25 = BM25Okapi(corpus_tokens)

    def retrieve(self, query_tokens: List[int], chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scores all chunks against a query and returns a new list of chunks 
        sorted by BM25 Okapi similarity score descending.
        
        Args:
            query_tokens: List of token IDs in the user's query.
            chunks: List of chunk dicts. Must align 1:1 in index with the corpus_tokens 
                    provided during initialization.
            
        Returns:
            List of chunk dicts with an added "bm25_score" key, sorted by relevance.
        """
        if not chunks:
            return []
            
        # Get BM25 scores for the tokenized query
        scores = self.bm25.get_scores(query_tokens)
        
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_copy = chunk.copy()
            chunk_copy["bm25_score"] = float(scores[i])
            scored_chunks.append(chunk_copy)
            
        # Sort by BM25 score in descending order
        scored_chunks.sort(key=lambda x: x["bm25_score"], reverse=True)
        return scored_chunks
