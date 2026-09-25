#!/usr/bin/env python3
"""Oráculo — Ingestion Scheduler Worker.

Long-running process designed to be managed by supervisord.
Checks for new or modified PDFs every ``--interval`` seconds (default: 3600 = 1 hour)
and runs the ingestion pipeline only when changes are detected.

Usage (standalone):
    python -m src.scheduler.worker --config configs/ingestion.yml

Usage (via supervisor):
    See configs/supervisor/oraculo-scheduler.conf
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("oraculo.scheduler")

# Graceful shutdown flag.
_shutdown_requested = False


def _handle_signal(signum: int, _frame: object) -> None:
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info("Received %s — requesting graceful shutdown.", sig_name)
    _shutdown_requested = True


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _run_detection(config_path: Path) -> dict:
    """Fast check: are there new/changed/deleted PDFs?"""
    from src.ingestion.config import IngestionConfig
    from src.scheduler.detector import detect_changes

    config = IngestionConfig.from_yaml(str(config_path))
    return detect_changes(
        input_dir=config.source.input_dir,
        base_dir=config.base_dir,
        recursive=config.source.recursive,
    )


def _run_ingestion(config_path: Path) -> dict:
    """Execute the full ingestion pipeline and return the summary."""
    from src.ingestion import IngestionConfig, IngestionPipeline

    config = IngestionConfig.from_yaml(str(config_path))
    summary = IngestionPipeline(config, progress=logger.info).run()
    return summary.to_dict()


def run_cycle(config_path: Path) -> None:
    """Single scheduler cycle: detect → ingest (if needed)."""
    logger.info("=== Cycle started at %s ===", _utc_now())

    try:
        changes = _run_detection(config_path)
    except Exception:
        logger.exception("Change detection failed — running full pipeline as fallback.")
        changes = {"has_changes": True, "new": [], "modified": [], "deleted": []}

    if not changes["has_changes"]:
        logger.info(
            "No changes detected (%d documents on disk, %d in snapshot). Sleeping.",
            changes.get("total_on_disk", 0),
            changes.get("total_in_snapshot", 0),
        )
        return

    new_count = len(changes.get("new", []))
    mod_count = len(changes.get("modified", []))
    del_count = len(changes.get("deleted", []))
    logger.info(
        "Changes detected — new: %d, modified: %d, deleted: %d. Starting ingestion.",
        new_count,
        mod_count,
        del_count,
    )

    if changes.get("new"):
        for path in changes["new"][:10]:
            logger.info("  + NEW: %s", path)
        if new_count > 10:
            logger.info("  ... and %d more.", new_count - 10)

    if changes.get("modified"):
        for path in changes["modified"][:10]:
            logger.info("  ~ MOD: %s", path)

    try:
        summary = _run_ingestion(config_path)
        logger.info(
            "Ingestion complete — processed: %d, skipped: %d, failed: %d, "
            "duration: %.1fs",
            summary["processed"],
            summary["skipped"],
            summary["failed"],
            summary["duration_seconds"],
        )
        if summary["failed"] > 0:
            logger.warning(
                "There were %d failure(s). Check failures.jsonl for details.",
                summary["failed"],
            )
    except Exception:
        logger.exception("Ingestion pipeline failed.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Oráculo ingestion scheduler — runs as a supervised process.",
    )
    parser.add_argument(
        "--config",
        default="configs/ingestion.yml",
        help="Path to the ingestion YAML config (default: configs/ingestion.yml).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Seconds between each check cycle (default: 3600 = 1 hour).",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Execute a single cycle and exit (useful for testing / cron).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(verbose=args.verbose)

    config_path = Path(args.config).expanduser().resolve()
    if not config_path.is_file():
        logger.error("Config file not found: %s", config_path)
        return 1

    interval = max(args.interval, 60)  # mínimo de 60 segundos

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("Oráculo Scheduler started.")
    logger.info("  Config : %s", config_path)
    logger.info("  Interval: %ds (%d min)", interval, interval // 60)
    logger.info("  Mode   : %s", "single-run" if args.run_once else "continuous")

    if args.run_once:
        run_cycle(config_path)
        return 0

    # Roda o primeiro ciclo imediatamente.
    run_cycle(config_path)

    while not _shutdown_requested:
        logger.info("Next check in %d minutes. Sleeping...", interval // 60)
        # Dorme em intervalos curtos para poder reagir rápido ao SIGTERM.
        deadline = time.monotonic() + interval
        while time.monotonic() < deadline and not _shutdown_requested:
            time.sleep(min(5.0, deadline - time.monotonic()))

        if not _shutdown_requested:
            run_cycle(config_path)

    logger.info("Scheduler shut down gracefully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
