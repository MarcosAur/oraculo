import os
from openai import OpenAI
from .base import LLMProvider

class OpenAIProvider(LLMProvider):
    """
    Concrete implementation of LLMProvider for OpenAI models.
    Uses 'OPENAI_API_KEY' environment variable.
    """
    
    def __init__(self):
        # Read the API key from custom name
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self.client = OpenAI(api_key=self.api_key)

    def generate(self, prompt: str, model: str, **kwargs) -> str:
        """
        Generates completion using OpenAI Chat Completions API.
        """
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1000)
        )
        return response.choices[0].message.content
