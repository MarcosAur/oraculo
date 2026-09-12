from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from src.api.routers import auth, qa
from src.api.config import settings

app = FastAPI(
    title="Oráculo API",
    description="API para o sistema RAG Oráculo com autenticação JWT e rotas de QA.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(qa.router, prefix="/qa", tags=["qa"])

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
