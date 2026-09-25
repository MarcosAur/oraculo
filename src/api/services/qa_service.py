from src.llm import GeminiProvider, OpenAIProvider, OpenRouterProvider
from src.pipelines import QAPipeline
from src.api.config import settings

PROVIDERS = {
    "openrouter": (OpenRouterProvider, "openai/gpt-4.1-mini"),
    "openai": (OpenAIProvider, "gpt-4.1-mini"),
    "gemini": (GeminiProvider, "gemini-2.0-flash"),
}

from sqlalchemy.orm import Session

def ask_question(question: str, provider: str = "openrouter", model: str | None = None, top_k: int = 3, db: Session | None = None) -> dict:
    if provider not in PROVIDERS:
        raise ValueError(f"Provedor '{provider}' não suportado.")
        
    provider_class, default_model = PROVIDERS[provider]
    pipeline = QAPipeline(
        llm_provider=provider_class(),
        db_session=db,
        retriever_mode=settings.RETRIEVER_MODE,
        embedding_model=settings.EMBEDDING_MODEL,
    )
    
    result = pipeline.answer(question, llm_model=model or default_model, top_k=top_k)
    return result
