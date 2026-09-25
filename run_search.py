from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.retrievers import DEFAULT_CHUNKS_PATH, DEFAULT_EMBEDDING_MODEL
from src.retrievers.factory import RETRIEVER_MODES, build_retriever


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Testa a busca (BM25, vetorial ou híbrida) sem chamar a LLM."
    )
    parser.add_argument("question", nargs="?", help="Pergunta a pesquisar.")
    parser.add_argument(
        "--retriever",
        choices=RETRIEVER_MODES,
        default=os.getenv("RETRIEVER_MODE", "hybrid"),
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument(
        "--model", default=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--full", action="store_true", help="Exibe o texto completo dos chunks."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.top_k < 1:
        raise SystemExit("Erro: --top-k deve ser maior que zero.")

    question = args.question or input("Pergunta: ").strip()
    if not question:
        raise SystemExit("Erro: informe uma pergunta.")

    try:
        retriever = build_retriever(
            args.retriever, args.chunks, embedding_model=args.model
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"Erro: {exc}") from exc

    results = retriever.retrieve(question, top_k=args.top_k)
    if not results:
        print("Nenhum trecho relacionado foi encontrado.")
        return 0

    print(f"\n{len(results)} resultado(s) [{args.retriever}] para: {question}\n")
    for position, chunk in enumerate(results, start=1):
        text = chunk["text"].strip()
        if not args.full and len(text) > 500:
            text = text[:500].rstrip() + "..."
        detail = ""
        if "scores" in chunk:
            detail = " (" + ", ".join(
                f"{name}: {value:.4f}" for name, value in chunk["scores"].items()
            ) + ")"
        print(f"[{position}] Score: {chunk['score']:.4f}{detail}")
        print(f"Fonte: {chunk.get('source_path', 'desconhecida')}")
        print(f"Páginas: {chunk.get('page_start', '?')}-{chunk.get('page_end', '?')}")
        print(text)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
