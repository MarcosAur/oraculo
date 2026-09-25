from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from src.ingestion.storage import BaseStore
from src.retrievers.embeddings import DEFAULT_EMBEDDING_MODEL, SentenceTransformerEmbedder
from src.retrievers.vector import CHROMA_DIR_NAME, ChromaVectorStore, DEFAULT_BASE_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Vetoriza os chunks de uma base ingerida (chunks.jsonl) e os "
            "armazena no ChromaDB. Só chunks novos são processados."
        )
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=DEFAULT_BASE_DIR,
        help=f"Pasta da base com chunks.jsonl (padrão: {DEFAULT_BASE_DIR}).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_EMBEDDING_MODEL,
        help=f"Modelo sentence-transformers (padrão: {DEFAULT_EMBEDDING_MODEL}).",
    )
    parser.add_argument("--device", default=None, help="cpu, cuda... (padrão: automático).")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Apaga o índice existente e vetoriza tudo novamente.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = BaseStore(args.base_dir)
    if not store.chunks_file.is_file():
        print(
            f"Erro: {store.chunks_file} não encontrado. Rode a ingestão primeiro.",
            file=sys.stderr,
        )
        return 2

    chroma_dir = args.base_dir / CHROMA_DIR_NAME
    if args.rebuild and chroma_dir.exists():
        shutil.rmtree(chroma_dir)

    chunks = store.load_chunks()
    print(f"{len(chunks)} chunk(s) em {store.chunks_file}")
    vector_store = ChromaVectorStore(
        chroma_dir,
        SentenceTransformerEmbedder(
            args.model, device=args.device, batch_size=args.batch_size
        ),
    )
    try:
        summary = vector_store.sync(chunks, progress=print)
    except KeyboardInterrupt:
        print("Indexação interrompida.", file=sys.stderr)
        return 130

    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
