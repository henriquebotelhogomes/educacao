"""Tests for make_point_id — determinism and uniqueness (ADR-011)."""

from __future__ import annotations

import uuid

from mentora_worker.vectorstore.qdrant_adapter import make_point_id

_DOC_V_ID_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_DOC_V_ID_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def test_same_inputs_produce_same_id() -> None:
    assert make_point_id(_DOC_V_ID_A, 0) == make_point_id(_DOC_V_ID_A, 0)


def test_different_chunk_index_produces_different_id() -> None:
    assert make_point_id(_DOC_V_ID_A, 0) != make_point_id(_DOC_V_ID_A, 1)


def test_different_document_version_produces_different_id() -> None:
    assert make_point_id(_DOC_V_ID_A, 0) != make_point_id(_DOC_V_ID_B, 0)


def test_result_is_valid_uuid_string() -> None:
    point_id = make_point_id(_DOC_V_ID_A, 42)
    parsed = uuid.UUID(point_id)
    assert str(parsed) == point_id


def test_result_is_uuid5_namespace_doc_version() -> None:
    """Verify the UUID5 is derived from (document_version_id, chunk_index)."""
    expected = str(uuid.uuid5(_DOC_V_ID_A, "7"))
    assert make_point_id(_DOC_V_ID_A, 7) == expected
