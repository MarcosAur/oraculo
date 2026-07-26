from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """
    Abstract Base Class that serves as the interface for all LLM providers.
    """
    
    @abstractmethod
    def generate(self, prompt: str, model: str, **kwargs) -> str:
        """
        Sends a prompt to the specified model and returns the generated text response.
        
        Args:
            prompt: The text prompt for the model.
            model: The identifier of the model (e.g. 'gpt-4o', 'gemini-1.5-flash').
            **kwargs: Extra parameters (like temperature, max_tokens, etc.).
            
        Returns:
            The generated response as a string.
        """
        pass
