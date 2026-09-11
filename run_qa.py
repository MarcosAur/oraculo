from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.llm import GeminiProvider, OpenAIProvider, OpenRouterProvider
from src.pipelines import QAPipeline
from src.retrievers import DEFAULT_CHUNKS_PATH


PROVIDERS = {
    "openrouter": (OpenRouterProvider, "openai/gpt-4.1-mini"),
    "openai": (OpenAIProvider, "gpt-4.1-mini"),
    "gemini": (GeminiProvider, "gemini-2.0-flash"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Consulta os PDFs ingeridos usando BM25 e uma LLM."
    )
    parser.add_argument("question", nargs="?", help="Pergunta para o RAG.")
    parser.add_argument(
        "--chunks", type=Path, default=DEFAULT_CHUNKS_PATH
    )
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default=os.getenv("LLM_PROVIDER", "openrouter"),
    )
    parser.add_argument("--model", default=os.getenv("LLM_MODEL"))
    parser.add_argument("--top-k", type=int, default=3)
    return parser


def main() -> int:
    load_dotenv()
    args = build_parser().parse_args()
    if args.top_k < 1:
        raise SystemExit("Erro: --top-k deve ser maior que zero.")

    question = args.question or input("Pergunta: ").strip()
    if not question:
        raise SystemExit("Erro: informe uma pergunta.")

    provider_class, default_model = PROVIDERS[args.provider]
    model = args.model or default_model
    try:
        pipeline = QAPipeline(
            llm_provider=provider_class(), chunks_path=args.chunks
        )
        result = pipeline.answer(question, llm_model=model, top_k=args.top_k)
    except (FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
        raise SystemExit(f"Erro: {exc}") from exc

    answer = result["answer"]
    print(f"\nResposta:\n{answer}")
    if result["sources"]:
        print("\nFontes recuperadas pelo BM25:")
        for chunk in result["sources"]:
            source_path = chunk.get("source_path", "desconhecida")
            score = chunk["score"]
            page_start = chunk.get("page_start", "?")
            page_end = chunk.get("page_end", "?")
            print(
                f"- {source_path} (score {score:.4f}, "
                f"páginas {page_start}-{page_end})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
