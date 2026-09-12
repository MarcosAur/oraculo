from __future__ import annotations

import argparse
from pathlib import Path

from src.retrievers import BM25Retriever, DEFAULT_CHUNKS_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Testa a busca BM25 sobre os chunks da ingestão de PDFs."
    )
    parser.add_argument("question", nargs="?", help="Pergunta a pesquisar.")
    parser.add_argument(
        "--chunks",
        type=Path,
        default=DEFAULT_CHUNKS_PATH,
        help=f"Arquivo JSONL de chunks (padrão: {DEFAULT_CHUNKS_PATH}).",
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
        from src.api.database import SessionLocal
        db = SessionLocal()
        retriever = BM25Retriever.from_jsonl_filtered(args.chunks, db)
        db.close()
    except Exception:
        retriever = BM25Retriever.from_jsonl(args.chunks)

    results = retriever.retrieve(question, top_k=args.top_k)
    if not results:
        print("Nenhum trecho relacionado foi encontrado.")
        return 0

    print(f"\n{len(results)} resultado(s) para: {question}\n")
    for position, chunk in enumerate(results, start=1):
        text = chunk["text"].strip()
        score = chunk["score"]
        source_path = chunk.get("source_path", "desconhecida")
        page_start = chunk.get("page_start", "?")
        page_end = chunk.get("page_end", "?")
        if not args.full and len(text) > 500:
            text = text[:500].rstrip() + "..."
        print(f"[{position}] Score BM25: {score:.4f}")
        print(f"Fonte: {source_path}")
        print(f"Páginas: {page_start}-{page_end}")
        print(text)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
