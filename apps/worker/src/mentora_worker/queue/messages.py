"""Redis Stream ingestion message model and parser."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ValidationError  # noqa: F401  (re-exported for callers)


class StreamMessage(BaseModel):
    """Base fields shared by all document lifecycle messages."""

    event_type: Literal["ingestion.requested", "document.delete_requested"]
    document_id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID


class IngestionMessage(StreamMessage):
    """Parsed ingestion job message from the Redis Stream (ADR-017)."""

    event_type: Literal["ingestion.requested"]
    job_id: UUID
    document_version_id: UUID
    storage_key: str


class DeletionMessage(StreamMessage):
    """Qdrant cleanup message emitted after a document soft delete."""

    event_type: Literal["document.delete_requested"]


def parse_stream_message(fields: dict[str, str]) -> IngestionMessage | DeletionMessage:
    """Validate and convert a Redis stream fields dict into an IngestionMessage."""
    if fields.get("event_type") == "document.delete_requested":
        return DeletionMessage.model_validate(fields)
    return IngestionMessage.model_validate(fields)
