from src.llm import GeminiProvider, OpenAIProvider, OpenRouterProvider
from src.pipelines import QAPipeline

PROVIDERS = {
    "openrouter": (OpenRouterProvider, "openai/gpt-4.1-mini"),
    "openai": (OpenAIProvider, "gpt-4.1-mini"),
    "gemini": (GeminiProvider, "gemini-2.0-flash"),
}

# Singleton para evitar recarregar o arquivo chunks.jsonl a cada request
_pipeline_instances = {}

def get_pipeline(provider: str) -> QAPipeline:
    if provider not in _pipeline_instances:
        provider_class, _ = PROVIDERS[provider]
        _pipeline_instances[provider] = QAPipeline(llm_provider=provider_class())
    return _pipeline_instances[provider]

def ask_question(question: str, provider: str = "openrouter", model: str | None = None, top_k: int = 3) -> dict:
    if provider not in PROVIDERS:
        raise ValueError(f"Provedor '{provider}' não suportado.")
        
    _, default_model = PROVIDERS[provider]
    pipeline = get_pipeline(provider)
    
    result = pipeline.answer(question, llm_model=model or default_model, top_k=top_k)
    return result
