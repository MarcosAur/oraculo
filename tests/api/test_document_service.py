from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.database import Base
from src.api.models.document import Chunk, Document
from src.api.services.document_service import sync_documents_after_ingestion


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def document_data(document_id="doc-1"):
    return {
        "document_id": document_id,
        "file_name": "manual.pdf",
        "relative_path": "manual.pdf",
        "source_path": "/pdfs/manual.pdf",
        "checksum": "a" * 64,
        "size_bytes": 100,
        "page_count": 1,
        "status": "success",
    }


def chunk_data(document_id="doc-1"):
    return {
        "chunk_id": f"chunk-{document_id}",
        "document_id": document_id,
        "chunk_index": 1,
        "text": "Conteúdo do manual",
        "token_count": 3,
        "page_start": 1,
        "page_end": 1,
        "source_path": "manual.pdf",
    }


def sync(db, documents, chunks):
    sync_documents_after_ingestion(db, [], documents, chunks)
    db.commit()


def test_sync_reactivates_soft_deleted_document_and_chunk():
    db = make_session()
    document = document_data()
    chunk = chunk_data()

    sync(db, [document], [chunk])
    sync(db, [], [])
    assert db.query(Document).one().deleted_at is not None
    assert db.query(Chunk).one().deleted_at is not None

    sync(db, [document], [chunk])

    assert db.query(Document).count() == 1
    assert db.query(Document).one().deleted_at is None
    assert db.query(Chunk).count() == 1
    assert db.query(Chunk).one().deleted_at is None


def test_sync_uses_snapshot_as_source_of_truth():
    db = make_session()
    old_document = document_data("old")
    new_document = document_data("new")
    sync(db, [old_document], [chunk_data("old")])

    sync(db, [new_document], [chunk_data("new")])

    active_ids = {
        row[0]
        for row in db.query(Document.document_id).filter(Document.deleted_at.is_(None)).all()
    }
    assert active_ids == {"new"}
