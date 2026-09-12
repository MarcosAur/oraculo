from fastapi import APIRouter, Depends, HTTPException
from src.api.schemas.qa import QuestionRequest, QuestionResponse
from src.api.dependencies import get_current_user
from src.api.models.user import User
from src.api.services.qa_service import ask_question
from src.api.config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/ask", response_model=QuestionResponse)
def ask(request: QuestionRequest, current_user: User = Depends(get_current_user)):
    try:
        # Usa provider/model do request ou cai nos padrões
        provider = request.provider or settings.LLM_PROVIDER
        model = request.model or settings.LLM_MODEL
        
        result = ask_question(
            question=request.question,
            provider=provider,
            model=model,
            top_k=request.top_k
        )
        
        # A resposta pode conter caminhos None, garantimos um default
        sources = []
        for s in result.get("sources", []):
            sources.append({
                "source_path": s.get("source_path", "desconhecido"),
                "score": s.get("score", 0.0),
                "page_start": s.get("page_start", "?"),
                "page_end": s.get("page_end", "?"),
                "text": s.get("text", "")
            })
            
        return {
            "question": result["question"],
            "answer": result["answer"],
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Erro ao processar pergunta: {e}")
        raise HTTPException(status_code=500, detail=str(e))
