from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.api.models.document import Chunk, Document


def _update_document(document: Document, data: dict, deleted_at=None) -> None:
    for field in (
        "file_name",
        "relative_path",
        "source_path",
        "checksum",
        "size_bytes",
        "page_count",
        "status",
    ):
        setattr(document, field, data[field])
    document.deleted_at = deleted_at


def _update_chunk(chunk: Chunk, data: dict, deleted_at=None) -> None:
    for field in (
        "document_id",
        "chunk_index",
        "text",
        "token_count",
        "page_start",
        "page_end",
        "source_path",
    ):
        setattr(chunk, field, data[field])
    chunk.deleted_at = deleted_at


def sync_documents_after_ingestion(
    db: Session,
    discovered_sources: list,
    pipeline_documents: list,
    pipeline_chunks: list,
) -> None:
    """Mirror the active JSONL snapshot into SQLite.

    The snapshot is the source of truth. Records are reactivated when a file
    returns with an ID already kept by the soft-delete history; inserting a new
    row in that case would violate the unique constraints on document/chunk IDs.
    """
    del discovered_sources  # Kept in the signature for compatibility with callers.

    now = datetime.now(timezone.utc)
    desired_document_ids = {item["document_id"] for item in pipeline_documents}
    desired_chunks_by_document: dict[str, list[dict]] = {}
    for item in pipeline_chunks:
        desired_chunks_by_document.setdefault(item["document_id"], []).append(item)

    for document in db.query(Document).filter(Document.deleted_at.is_(None)).all():
        if document.document_id not in desired_document_ids:
            document.deleted_at = now
            for chunk in document.chunks:
                chunk.deleted_at = now

    for document_data in pipeline_documents:
        document_id = document_data["document_id"]
        document = db.query(Document).filter(Document.document_id == document_id).one_or_none()
        if document is None:
            document = Document(document_id=document_id)
            db.add(document)
        _update_document(document, document_data)

        desired_chunks = {
            item["chunk_id"]: item
            for item in desired_chunks_by_document.get(document_id, [])
        }
        existing_chunks = {
            chunk.chunk_id: chunk
            for chunk in db.query(Chunk).filter(Chunk.document_id == document_id).all()
        }

        for chunk_id, chunk in existing_chunks.items():
            if chunk_id not in desired_chunks:
                chunk.deleted_at = now

        for chunk_id, chunk_data in desired_chunks.items():
            chunk = existing_chunks.get(chunk_id)
            if chunk is None:
                chunk = db.query(Chunk).filter(Chunk.chunk_id == chunk_id).one_or_none()
            if chunk is None:
                chunk = Chunk(chunk_id=chunk_id)
                db.add(chunk)
            _update_chunk(chunk, chunk_data)
