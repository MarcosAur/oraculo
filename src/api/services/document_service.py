from sqlalchemy.orm import Session
from datetime import datetime, timezone
from src.api.models.document import Document, Chunk

def sync_documents_after_ingestion(db: Session, discovered_sources: list, pipeline_documents: list, pipeline_chunks: list):
    now = datetime.now(timezone.utc)
    
    # Map discovered sources by relative_path
    discovered_paths = {src.relative_path for src in discovered_sources}
    
    # Soft delete documents not in discovered sources anymore
    active_docs = db.query(Document).filter(Document.deleted_at.is_(None)).all()
    for doc in active_docs:
        if doc.relative_path not in discovered_paths:
            doc.deleted_at = now
            for chunk in doc.chunks:
                chunk.deleted_at = now
    
    # Map pipeline outputs
    pipeline_doc_map = {d["relative_path"]: d for d in pipeline_documents}
    pipeline_chunk_map = {}
    for c in pipeline_chunks:
        pipeline_chunk_map.setdefault(c["document_id"], []).append(c)

    # Process all discovered and successfully ingested documents
    for rel_path, p_doc in pipeline_doc_map.items():
        existing = db.query(Document).filter(
            Document.relative_path == rel_path, 
            Document.deleted_at.is_(None)
        ).first()
        
        if existing:
            if existing.checksum != p_doc["checksum"]:
                # Document changed: soft delete the old one, insert the new one
                existing.deleted_at = now
                for chunk in existing.chunks:
                    chunk.deleted_at = now
            else:
                # Document unchanged, ignore
                continue
                
        # Insert new doc
        new_doc = Document(
            document_id=p_doc["document_id"],
            file_name=p_doc["file_name"],
            relative_path=p_doc["relative_path"],
            source_path=p_doc["source_path"],
            checksum=p_doc["checksum"],
            size_bytes=p_doc["size_bytes"],
            page_count=p_doc["page_count"],
            status=p_doc["status"]
        )
        db.add(new_doc)
        
        # Insert chunks for the new doc
        for p_chunk in pipeline_chunk_map.get(p_doc["document_id"], []):
            new_chunk = Chunk(
                chunk_id=p_chunk["chunk_id"],
                document_id=p_chunk["document_id"],
                chunk_index=p_chunk["chunk_index"],
                text=p_chunk["text"],
                token_count=p_chunk["token_count"],
                page_start=p_chunk["page_start"],
                page_end=p_chunk["page_end"],
                source_path=p_chunk["source_path"]
            )
            db.add(new_chunk)
