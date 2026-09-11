from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Iterable


class BaseStore:
    """Persists one versioned ingestion base using atomic metadata snapshots."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.documents_dir = base_dir / "documents"
        self.staging_root = base_dir / ".staging"
        self.documents_file = base_dir / "documents.jsonl"
        self.chunks_file = base_dir / "chunks.jsonl"
        self.failures_file = base_dir / "failures.jsonl"
        self.manifest_file = base_dir / "manifest.json"

    def initialize(self) -> None:
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.staging_root.mkdir(parents=True, exist_ok=True)

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records = []
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL in {path} at line {line_number}: {exc}"
                    ) from exc
        return records

    def load_documents(self) -> list[dict[str, Any]]:
        return self._read_jsonl(self.documents_file)

    def load_chunks(self) -> list[dict[str, Any]]:
        return self._read_jsonl(self.chunks_file)

    def create_staging_dir(self) -> Path:
        self.initialize()
        return Path(tempfile.mkdtemp(prefix="document-", dir=self.staging_root))

    def discard_staging(self, staging_dir: Path) -> None:
        if staging_dir.exists() and staging_dir.parent == self.staging_root:
            shutil.rmtree(staging_dir)

    def commit_document(self, staging_dir: Path, document_id: str) -> Path:
        destination = self.documents_dir / document_id
        backup = self.staging_root / f"backup-{document_id}-{uuid.uuid4().hex}"
        had_previous = destination.exists()

        if had_previous:
            os.replace(destination, backup)
        try:
            os.replace(staging_dir, destination)
        except Exception:
            if had_previous and backup.exists():
                os.replace(backup, destination)
            raise
        if backup.exists():
            shutil.rmtree(backup)
        return destination

    def remove_document_artifacts(self, document_id: str) -> None:
        path = self.documents_dir / document_id
        if path.exists() and path.parent == self.documents_dir:
            shutil.rmtree(path)

    def _atomic_text_write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def _write_jsonl(
        self, path: Path, records: Iterable[dict[str, Any]]
    ) -> None:
        content = "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        )
        self._atomic_text_write(path, content)

    def write_snapshot(
        self,
        documents: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
        failures: list[dict[str, Any]],
        manifest: dict[str, Any],
    ) -> None:
        documents = sorted(documents, key=lambda item: item["relative_path"].casefold())
        chunks = sorted(
            chunks,
            key=lambda item: (item["document_id"], item["chunk_index"]),
        )
        failures = sorted(failures, key=lambda item: item["relative_path"].casefold())
        self._write_jsonl(self.documents_file, documents)
        self._write_jsonl(self.chunks_file, chunks)
        self._write_jsonl(self.failures_file, failures)
        self._atomic_text_write(
            self.manifest_file,
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )

