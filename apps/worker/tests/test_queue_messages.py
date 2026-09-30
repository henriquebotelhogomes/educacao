"""Tests for parse_stream_message — no external services required."""

from __future__ import annotations

import pytest
from mentora_worker.queue.messages import DeletionMessage, IngestionMessage, parse_stream_message
from pydantic import ValidationError

_VALID_FIELDS = {
    "event_type": "ingestion.requested",
    "job_id": "11111111-1111-1111-1111-111111111111",
    "document_id": "00000000-0000-0000-0000-000000000000",
    "document_version_id": "22222222-2222-2222-2222-222222222222",
    "tenant_id": "33333333-3333-3333-3333-333333333333",
    "knowledge_base_id": "44444444-4444-4444-4444-444444444444",
    "storage_key": "uploads/tenant1/doc.pdf",
}


def test_valid_fields_parse_correctly() -> None:
    """All UUID fields should round-trip through parse_stream_message."""
    msg = parse_stream_message(_VALID_FIELDS)
    assert isinstance(msg, IngestionMessage)
    assert str(msg.job_id) == "11111111-1111-1111-1111-111111111111"
    assert str(msg.document_version_id) == "22222222-2222-2222-2222-222222222222"
    assert str(msg.tenant_id) == "33333333-3333-3333-3333-333333333333"
    assert str(msg.knowledge_base_id) == "44444444-4444-4444-4444-444444444444"
    assert msg.storage_key == "uploads/tenant1/doc.pdf"


def test_missing_required_field_raises_validation_error() -> None:
    fields = {k: v for k, v in _VALID_FIELDS.items() if k != "job_id"}
    with pytest.raises(ValidationError):
        parse_stream_message(fields)


def test_invalid_uuid_raises_validation_error() -> None:
    fields = {**_VALID_FIELDS, "tenant_id": "not-a-uuid"}
    with pytest.raises(ValidationError):
        parse_stream_message(fields)


def test_deletion_message_requires_only_tenant_and_document_scope() -> None:
    message = parse_stream_message(
        {
            "event_type": "document.delete_requested",
            "document_id": "00000000-0000-0000-0000-000000000000",
            "tenant_id": "33333333-3333-3333-3333-333333333333",
            "knowledge_base_id": "44444444-4444-4444-4444-444444444444",
        }
    )

    assert isinstance(message, DeletionMessage)
