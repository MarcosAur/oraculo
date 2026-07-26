import os
import google.generativeai as genai
from .base import LLMProvider

class GeminiProvider(LLMProvider):
    """
    Concrete implementation of LLMProvider for Google Gemini models.
    Uses 'GEMINI_API_KEY' environment variable.
    """
    
    def __init__(self):
        # Read the API key from custom name
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        genai.configure(api_key=self.api_key)

    def generate(self, prompt: str, model: str, **kwargs) -> str:
        """
        Generates completion using Google Gemini API.
        """
        gemini_model = genai.GenerativeModel(model)
        generation_config = genai.types.GenerationConfig(
            temperature=kwargs.get("temperature", 0.7),
            max_output_tokens=kwargs.get("max_tokens", 1000)
        )
        response = gemini_model.generate_content(
            prompt,
            generation_config=generation_config
        )
        return response.text
