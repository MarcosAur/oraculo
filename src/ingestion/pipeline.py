from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .chunkers import MarkdownChunker
from .classifier import PdfClassifier, PdfType
from .config import IngestionConfig
from .extractors import DocumentExtractor, NativePdfExtractor, PaddleOcrPdfExtractor
from .models import (
    ChunkRecord,
    DocumentRecord,
    FailureRecord,
    IngestionSummary,
    SCHEMA_VERSION,
    SourceDocument,
)
from .normalizers import MarkdownNormalizer
from .sources import DirectoryPdfSource
from .storage import BaseStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IngestionPipeline:
    """Coordinates discovery, extraction, chunking and incremental persistence."""

    def __init__(
        self,
        config: IngestionConfig,
        *,
        extractor: DocumentExtractor | None = None,
        native_extractor: DocumentExtractor | None = None,
        classifier: PdfClassifier | None = None,
        source: DirectoryPdfSource | None = None,
        store: BaseStore | None = None,
        vector_store: Any | None = None,
        progress: Callable[[str], None] | None = None,
    ):
        self.config = config
        self.source = source or DirectoryPdfSource(
            config.source.input_dir, config.source.recursive
        )
        self.ocr_extractor = extractor or PaddleOcrPdfExtractor(config.paddle_ocr)
        self.native_extractor = native_extractor or NativePdfExtractor()
        self.classifier = classifier or PdfClassifier(
            min_chars_per_page=config.classification.min_chars_per_page,
            native_threshold=config.classification.native_threshold,
            scanned_threshold=config.classification.scanned_threshold,
        )
        self.normalizer = MarkdownNormalizer()
        self.chunker = MarkdownChunker(config.chunking)
        self.store = store or BaseStore(config.base_dir)
        self.vector_store = vector_store
        self.progress = progress or (lambda _message: None)

    def _checksum(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _document_id(self, source: SourceDocument, checksum: str) -> str:
        identity = f"{source.relative_path}\0{checksum}".encode("utf-8")
        return hashlib.sha256(identity).hexdigest()[:24]

    def _chunk_id(self, document_id: str, index: int, text: str) -> str:
        identity = f"{document_id}\0{index}\0{text}".encode("utf-8")
        return hashlib.sha256(identity).hexdigest()[:32]

    def _sync_vector_store(self, chunks: list[dict]) -> dict | None:
        """Mirrors chunks.jsonl into ChromaDB. Failures keep the JSONL snapshot."""
        if self.vector_store is None and not self.config.vector_store.enabled:
            return None
        try:
            if self.vector_store is None:
                from src.retrievers.embeddings import SentenceTransformerEmbedder
                from src.retrievers.vector import ChromaVectorStore

                settings = self.config.vector_store
                self.vector_store = ChromaVectorStore.for_base(
                    self.config.base_dir,
                    SentenceTransformerEmbedder(
                        settings.embedding_model,
                        device=settings.device,
                        batch_size=settings.batch_size,
                    ),
                )
            self.progress("Updating vector index...")
            summary = self.vector_store.sync(chunks, progress=self.progress).to_dict()
            self.progress(f"Vector index: {summary}")
            return summary
        except Exception as exc:
            self.progress(
                f"Failed to update vector index: {exc}. "
                "Retry with: python -m src.cli.index_vectors"
            )
            return {"error": f"{type(exc).__name__}: {exc}"}

    def run(self) -> IngestionSummary:
        started = time.monotonic()
        self.store.initialize()
        discovered = self.source.discover()
        self.progress(f"Discovered {len(discovered)} PDF file(s).")

        previous_documents = self.store.load_documents()
        previous_chunks = self.store.load_chunks()
        active_documents = {
            item["relative_path"]: item for item in previous_documents
        }
        chunks_by_document: dict[str, list[dict]] = {}
        for chunk in previous_chunks:
            chunks_by_document.setdefault(chunk["document_id"], []).append(chunk)

        processed = 0
        skipped = 0
        failures: list[dict] = []
        stale_document_ids: set[str] = set()

        for position, source in enumerate(discovered, start=1):
            staging_dir: Path | None = None
            try:
                path = Path(source.path)
                checksum = self._checksum(path)
                previous = active_documents.get(source.relative_path)
                previous_markdown_exists = bool(
                    previous
                    and (self.config.base_dir / previous["markdown_path"]).is_file()
                )
                if (
                    previous
                    and previous.get("checksum") == checksum
                    and previous_markdown_exists
                    and not self.config.runtime.force
                ):
                    skipped += 1
                    self.progress(
                        f"[{position}/{len(discovered)}] Skipped unchanged: "
                        f"{source.relative_path}"
                    )
                    continue

                self.progress(
                    f"[{position}/{len(discovered)}] Processing: {source.relative_path}"
                )

                # Classify the PDF to choose the right extractor.
                classification = self.classifier.classify(path)
                if classification.pdf_type == PdfType.NATIVE:
                    extractor = self.native_extractor
                    label = "native"
                else:
                    extractor = self.ocr_extractor
                    label = classification.pdf_type.value

                self.progress(
                    f"  → Classified as {label} "
                    f"({classification.native_pages}/{classification.total_pages} "
                    f"text pages)"
                )

                document_id = self._document_id(source, checksum)
                staging_dir = self.store.create_staging_dir()
                extraction = extractor.extract(source, staging_dir)
                raw_path = staging_dir / "document.raw.md"
                markdown_path = staging_dir / "document.md"
                if not raw_path.is_file() or raw_path.stat().st_size == 0:
                    raise ValueError("Extractor did not produce document.raw.md.")

                markdown = self.normalizer.normalize_file(raw_path, markdown_path)
                drafts = self.chunker.create_chunks(markdown)
                if not drafts:
                    raise ValueError("The extracted document did not produce any chunks.")

                document_dir = Path("documents") / document_id
                now = _utc_now()
                document = DocumentRecord(
                    document_id=document_id,
                    source_path=source.path,
                    relative_path=source.relative_path,
                    file_name=source.file_name,
                    checksum=checksum,
                    size_bytes=source.size_bytes,
                    page_count=extraction.page_count,
                    extraction_method=extraction.extraction_method,
                    languages=extraction.languages,
                    status=extraction.status,
                    created_at=now,
                    markdown_path=(document_dir / "document.md").as_posix(),
                    raw_markdown_path=(document_dir / "document.raw.md").as_posix(),
                    assets_dir=(document_dir / "assets").as_posix(),
                    metadata={
                        "warnings": extraction.warnings,
                        "pdf_type": classification.pdf_type.value,
                    },
                )
                chunks = [
                    ChunkRecord(
                        chunk_id=self._chunk_id(document_id, index, draft.text),
                        document_id=document_id,
                        chunk_index=index,
                        text=draft.text,
                        token_count=draft.token_count,
                        page_start=draft.page_start,
                        page_end=draft.page_end,
                        section_path=draft.section_path,
                        source_path=source.relative_path,
                        metadata={
                            "overlap_token_count": draft.overlap_token_count,
                            "tokenizer_model": self.config.chunking.tokenizer_model,
                        },
                    ).to_dict()
                    for index, draft in enumerate(drafts, start=1)
                ]

                self.store.commit_document(staging_dir, document_id)
                staging_dir = None
                if previous and previous["document_id"] != document_id:
                    stale_document_ids.add(previous["document_id"])
                    chunks_by_document.pop(previous["document_id"], None)
                active_documents[source.relative_path] = document.to_dict()
                chunks_by_document[document_id] = chunks
                processed += 1
            except Exception as exc:
                failure = FailureRecord(
                    source_path=source.path,
                    relative_path=source.relative_path,
                    stage="ingestion",
                    error_type=type(exc).__name__,
                    message=str(exc),
                    occurred_at=_utc_now(),
                ).to_dict()
                failures.append(failure)
                self.progress(
                    f"[{position}/{len(discovered)}] Failed: "
                    f"{source.relative_path}: {exc}"
                )
                if not self.config.runtime.continue_on_error:
                    raise
            finally:
                if staging_dir is not None:
                    self.store.discard_staging(staging_dir)

        all_documents = list(active_documents.values())
        all_chunks = [
            chunk
            for document_chunks in chunks_by_document.values()
            for chunk in document_chunks
        ]
        duration = time.monotonic() - started
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "base_name": self.config.output.base_name,
            "generated_at": _utc_now(),
            "input_directory": str(self.config.source.input_dir),
            "configuration": self.config.to_manifest_dict(),
            "statistics": {
                "discovered": len(discovered),
                "processed": processed,
                "skipped": skipped,
                "failed": len(failures),
                "active_documents": len(all_documents),
                "active_chunks": len(all_chunks),
                "duration_seconds": round(duration, 3),
            },
        }
        self.store.write_snapshot(
            all_documents, all_chunks, failures, manifest
        )
        for document_id in stale_document_ids:
            self.store.remove_document_artifacts(document_id)

        vector_index = self._sync_vector_store(all_chunks)

        # Sincroniza estado com o Banco de Dados SQLite
        try:
            from src.api.database import SessionLocal
            from src.api.services.document_service import sync_documents_after_ingestion
            db = SessionLocal()
            try:
                sync_documents_after_ingestion(
                    db=db,
                    discovered_sources=discovered,
                    pipeline_documents=all_documents,
                    pipeline_chunks=all_chunks
                )
                db.commit()
            except Exception as exc:
                self.progress(f"Failed to sync with SQLite: {exc}")
                db.rollback()
            finally:
                db.close()
        except ImportError:
            self.progress("SQLite sync skipped (API module not found).")


        return IngestionSummary(
            base_name=self.config.output.base_name,
            discovered=len(discovered),
            processed=processed,
            skipped=skipped,
            failed=len(failures),
            active_documents=len(all_documents),
            active_chunks=len(all_chunks),
            duration_seconds=round(duration, 3),
            output_dir=str(self.config.base_dir),
            vector_index=vector_index,
        )
