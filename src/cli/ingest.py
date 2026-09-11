from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from src.ingestion import IngestionConfig, IngestionPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest PDF files from a directory using PaddleOCR."
    )
    parser.add_argument("--config", help="Path to an ingestion YAML file.")
    parser.add_argument("--input", help="PDF input directory (overrides YAML).")
    parser.add_argument("--base", help="Base name (overrides YAML).")
    parser.add_argument("--output", help="Output root directory (overrides YAML).")
    parser.add_argument(
        "--force", action="store_true", help="Reprocess unchanged documents."
    )
    return parser


def load_config(args: argparse.Namespace) -> IngestionConfig:
    if args.config:
        config = IngestionConfig.from_yaml(args.config)
    elif args.input:
        config = IngestionConfig.for_directory(
            input_dir=args.input,
            base_name=args.base or "default",
            output_dir=args.output or "data/bases",
            force=args.force,
        )
    else:
        raise ValueError("Provide --config or --input.")

    if args.input:
        config = replace(
            config,
            source=replace(
                config.source, input_dir=Path(args.input).expanduser().resolve()
            ),
        )
    if args.base:
        config = replace(config, output=replace(config.output, base_name=args.base))
    if args.output:
        config = replace(
            config,
            output=replace(
                config.output,
                root_dir=Path(args.output).expanduser().resolve(),
            ),
        )
    if args.force:
        config = replace(config, runtime=replace(config.runtime, force=True))
    config.validate()
    return config


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args)
        summary = IngestionPipeline(config, progress=print).run()
    except (FileNotFoundError, NotADirectoryError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
        return 2
    except KeyboardInterrupt:
        print("Ingestion interrupted.", file=sys.stderr)
        return 130

    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 2 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
