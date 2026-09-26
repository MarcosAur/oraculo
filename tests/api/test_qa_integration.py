import pytest
from pydantic import ValidationError

from src.api.schemas.qa import QuestionRequest
from src.api.services import qa_service


def test_question_request_validates_retriever_options():
    request = QuestionRequest(question="  Como funciona?  ", retriever_mode="vector", top_k=5)

    assert request.question == "Como funciona?"
    assert request.retriever_mode == "vector"
    assert request.top_k == 5

    with pytest.raises(ValidationError):
        QuestionRequest(question=" ", retriever_mode="invalid", top_k=0)


def test_service_passes_selected_retriever_to_pipeline(monkeypatch):
    pipeline_args = {}

    class FakeProvider:
        pass

    class FakePipeline:
        def __init__(self, **kwargs):
            pipeline_args.update(kwargs)

        def answer(self, question, llm_model, top_k):
            return {"question": question, "answer": "Resposta", "sources": []}

    monkeypatch.setitem(qa_service.PROVIDERS, "fake", (FakeProvider, "fake-model"))
    monkeypatch.setattr(qa_service, "QAPipeline", FakePipeline)

    result = qa_service.ask_question(
        "Pergunta",
        provider="fake",
        retriever_mode="vector",
        top_k=5,
    )

    assert pipeline_args["retriever_mode"] == "vector"
    assert result["retriever_mode"] == "vector"
