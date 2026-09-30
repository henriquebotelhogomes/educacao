"""Document ingestion domain types and state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    SUPERSEDED = "SUPERSEDED"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True)
class DocumentRecord:
    id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID
    filename: str
    content_hash: str
    size_bytes: int
    mime_type: str


@dataclass(frozen=True)
class DocumentVersion:
    id: UUID
    document_id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID
    version_number: int
    storage_key: str
    status: DocumentStatus
    error_message: str | None
    page_count: int | None
    chunk_count: int


@dataclass(frozen=True)
class IngestionJob:
    id: UUID
    document_id: UUID
    document_version_id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID
    status: JobStatus
    current_stage: str
    error_message: str | None
    attempt_count: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
