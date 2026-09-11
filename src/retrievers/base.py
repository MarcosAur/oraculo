from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseRetriever(ABC):
    """
    Abstract Base Class representing the interface for all search retrievers.
    """
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieves the top_k most relevant chunks for a given raw text query.
        
        Args:
            query: The raw string query from the user.
            top_k: The number of relevant documents to return.
            **kwargs: Additional search or filter parameters.
            
        Returns:
            A list of dictionary chunks sorted by relevance, each containing a 'score' key.
        """
        raise NotImplementedError
