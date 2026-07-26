import os
from openai import OpenAI
from .base import LLMProvider

class OpenRouterProvider(LLMProvider):
    """
    Concrete implementation of LLMProvider for OpenRouter models.
    Uses 'OPENROUTER_API_KEY' environment variable.
    """
    
    def __init__(self):
        # Read the API key from custom name
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set.")
        # OpenRouter uses the OpenAI client pointed to their base URL
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )

    def generate(self, prompt: str, model: str, **kwargs) -> str:
        """
        Generates completion using OpenRouter API.
        """
        # OpenRouter suggests adding referer and title headers
        extra_headers = {
            "HTTP-Referer": kwargs.get("referer", "https://github.com/oraculo-rag"),
            "X-Title": kwargs.get("app_title", "Oraculo RAG")
        }
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            extra_headers=extra_headers,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1000)
        )
        return response.choices[0].message.content
