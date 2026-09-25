from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SourceDocument:
    """A PDF discovered in the configured input directory."""

    path: str
    relative_path: str
    file_name: str
    size_bytes: int


@dataclass(frozen=True)
class ExtractionResult:
    """Metadata returned by an extractor after writing document artifacts."""

    page_count: int
    extraction_method: str
    status: str
    languages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    source_path: str
    relative_path: str
    file_name: str
    checksum: str
    size_bytes: int
    page_count: int
    extraction_method: str
    languages: list[str]
    status: str
    created_at: str
    markdown_path: str
    raw_markdown_path: str
    assets_dir: str
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    token_count: int
    page_start: int
    page_end: int
    section_path: list[str]
    source_path: str
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FailureRecord:
    source_path: str
    relative_path: str
    stage: str
    error_type: str
    message: str
    occurred_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IngestionSummary:
    base_name: str
    discovered: int
    processed: int
    skipped: int
    failed: int
    active_documents: int
    active_chunks: int
    duration_seconds: float
    output_dir: str
    vector_index: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
