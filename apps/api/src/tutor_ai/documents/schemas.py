"""Public document DTOs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from tutor_ai.documents.domain import DocumentStatus, JobStatus


class DocumentResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    filename: str
    content_hash: str
    size_bytes: int
    status: DocumentStatus
    version_id: UUID
    ingestion_job_id: UUID
    error_message: str | None = None
    created_at: datetime


class DocumentStatusResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: JobStatus
    current_stage: str
    attempt_count: int
    error_message: str | None
    updated_at: datetime
