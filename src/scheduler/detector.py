"""Fast change detection for the ingestion directory.

Compares the current filesystem state against the last ingestion snapshot
to decide whether a full pipeline run is necessary.  This avoids loading
PaddleOCR (heavy) when nothing changed.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            stripped = line.strip()
            if stripped:
                try:
                    records.append(json.loads(stripped))
                except json.JSONDecodeError:
                    continue
    return records


def _file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def detect_changes(
    input_dir: Path,
    base_dir: Path,
    *,
    recursive: bool = True,
) -> dict[str, Any]:
    """Compare the PDF directory against the stored documents snapshot.

    Returns a dict with:
      - ``has_changes``: whether new/modified/deleted PDFs were detected.
      - ``new``: list of relative paths that are not in the snapshot.
      - ``modified``: list of relative paths whose checksum changed.
      - ``deleted``: list of relative paths present in the snapshot but
        missing from disk.
      - ``total_on_disk``: number of PDFs currently on disk.
      - ``total_in_snapshot``: number of documents in the last snapshot.
    """
    documents_file = base_dir / "documents.jsonl"
    known: dict[str, str] = {}
    for record in _read_jsonl(documents_file):
        rel_path = record.get("relative_path", "")
        checksum = record.get("checksum", "")
        if rel_path:
            known[rel_path] = checksum

    if not input_dir.is_dir():
        return {
            "has_changes": False,
            "new": [],
            "modified": [],
            "deleted": [],
            "total_on_disk": 0,
            "total_in_snapshot": len(known),
            "reason": f"Input directory not found: {input_dir}",
        }

    # Discover current PDFs on disk.
    iterator = input_dir.rglob("*") if recursive else input_dir.iterdir()
    current_paths = sorted(
        (
            p
            for p in iterator
            if p.is_file() and p.suffix.lower() == ".pdf"
        ),
        key=lambda p: p.relative_to(input_dir).as_posix().casefold(),
    )

    on_disk: dict[str, Path] = {
        p.relative_to(input_dir).as_posix(): p for p in current_paths
    }

    new: list[str] = []
    modified: list[str] = []

    for rel_path, abs_path in on_disk.items():
        if rel_path not in known:
            new.append(rel_path)
        else:
            disk_checksum = _file_checksum(abs_path)
            if disk_checksum != known[rel_path]:
                modified.append(rel_path)

    deleted = [rel for rel in known if rel not in on_disk]

    has_changes = bool(new or modified or deleted)

    # Also flag when there's no snapshot at all (first run).
    if not documents_file.exists() and on_disk:
        has_changes = True

    return {
        "has_changes": has_changes,
        "new": new,
        "modified": modified,
        "deleted": deleted,
        "total_on_disk": len(on_disk),
        "total_in_snapshot": len(known),
    }
