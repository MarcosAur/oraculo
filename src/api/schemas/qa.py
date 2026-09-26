from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RetrieverMode = Literal["bm25", "vector", "hybrid"]

class QuestionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1)
    provider: str | None = None
    model: str | None = None
    top_k: int = Field(default=3, ge=1, le=20)
    retriever_mode: RetrieverMode | None = None

class SourceItem(BaseModel):
    source_path: str
    score: float
    page_start: int | str
    page_end: int | str
    text: str

class QuestionResponse(BaseModel):
    question: str
    answer: str
    retriever_mode: RetrieverMode
    sources: list[SourceItem]
