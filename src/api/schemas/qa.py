from pydantic import BaseModel
from typing import Any

class QuestionRequest(BaseModel):
    question: str
    provider: str | None = None
    model: str | None = None
    top_k: int = 3

class SourceItem(BaseModel):
    source_path: str
    score: float
    page_start: int | str
    page_end: int | str
    text: str

class QuestionResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceItem] | list[Any]
