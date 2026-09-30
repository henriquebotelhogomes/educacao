"""Tenant-scoped document persistence and transactional outbox writes."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from tutor_ai.documents.domain import (
    DocumentRecord,
    DocumentStatus,
    DocumentVersion,
    IngestionJob,
    JobStatus,
)

Connection = psycopg.Connection[dict[str, Any]]
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
CHUNKING_STRATEGY_VERSION = "docling-structural-512-64-v1"


def _uuid(row: dict[str, Any], field: str) -> UUID:
    return UUID(str(row[field]))


def _document(row: dict[str, Any]) -> DocumentRecord:
    return DocumentRecord(
        id=_uuid(row, "id"),
        tenant_id=_uuid(row, "tenant_id"),
        knowledge_base_id=_uuid(row, "knowledge_base_id"),
        filename=str(row["filename"]),
        content_hash=str(row["content_hash"]),
        size_bytes=int(row["size_bytes"]),
        mime_type=str(row["mime_type"]),
    )


def _version(row: dict[str, Any]) -> DocumentVersion:
    return DocumentVersion(
        id=_uuid(row, "id"),
        document_id=_uuid(row, "document_id"),
        tenant_id=_uuid(row, "tenant_id"),
        knowledge_base_id=_uuid(row, "knowledge_base_id"),
        version_number=int(row["version_number"]),
        storage_key=str(row["storage_key"]),
        status=DocumentStatus(str(row["status"])),
        error_message=row["error_message"] if isinstance(row["error_message"], str) else None,
        page_count=int(row["page_count"]) if row["page_count"] is not None else None,
        chunk_count=int(row["chunk_count"]),
    )


def _job(row: dict[str, Any]) -> IngestionJob:
    return IngestionJob(
        id=_uuid(row, "id"),
        document_id=_uuid(row, "document_id"),
        document_version_id=_uuid(row, "document_version_id"),
        tenant_id=_uuid(row, "tenant_id"),
        knowledge_base_id=_uuid(row, "knowledge_base_id"),
        status=JobStatus(str(row["status"])),
        current_stage=str(row["current_stage"]),
        error_message=row["error_message"] if isinstance(row["error_message"], str) else None,
        attempt_count=int(row["attempt_count"]),
        updated_at=row["updated_at"],
    )


def get_or_create_default_knowledge_base(connection: Connection, tenant_id: UUID) -> UUID:
    row = connection.execute(
        """
        SELECT id FROM knowledge_base
        WHERE tenant_id = %s AND is_default AND deleted_at IS NULL
        """,
        (tenant_id,),
    ).fetchone()
    if row is not None:
        return _uuid(row, "id")

    knowledge_base_id = uuid4()
    connection.execute(
        """
        INSERT INTO knowledge_base (id, tenant_id, name, is_default)
        VALUES (%s, %s, 'Minha biblioteca', true)
        ON CONFLICT DO NOTHING
        """,
        (knowledge_base_id, tenant_id),
    )
    row = connection.execute(
        """
        SELECT id FROM knowledge_base
        WHERE tenant_id = %s AND is_default AND deleted_at IS NULL
        """,
        (tenant_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Default knowledge base was not created")
    return _uuid(row, "id")


def count_active_documents(connection: Connection) -> int:
    row = connection.execute(
        "SELECT count(*) AS total FROM document WHERE deleted_at IS NULL"
    ).fetchone()
    return int(row["total"]) if row else 0


def find_active_document_by_hash(
    connection: Connection,
    content_hash: str,
) -> tuple[DocumentRecord, DocumentVersion, IngestionJob] | None:
    row = connection.execute(
        """
        SELECT
            d.id, d.tenant_id, d.knowledge_base_id, d.filename, d.content_hash, d.size_bytes,
            d.mime_type,
            dv.id AS version_id, dv.version_number, dv.storage_key, dv.status AS version_status,
            dv.error_message AS version_error_message, dv.page_count, dv.chunk_count,
            j.id AS job_id, j.status AS job_status, j.current_stage,
            j.error_message AS job_error_message
        FROM document d
        JOIN document_version dv ON dv.document_id = d.id
        JOIN ingestion_job j ON j.document_version_id = dv.id
        WHERE d.content_hash = %s AND d.deleted_at IS NULL
        ORDER BY dv.version_number DESC
        LIMIT 1
        """,
        (content_hash,),
    ).fetchone()
    if row is None:
        return None
    document = _document(row)
    version = DocumentVersion(
        id=UUID(str(row["version_id"])),
        document_id=document.id,
        tenant_id=document.tenant_id,
        knowledge_base_id=document.knowledge_base_id,
        version_number=int(row["version_number"]),
        storage_key=str(row["storage_key"]),
        status=DocumentStatus(str(row["version_status"])),
        error_message=row["version_error_message"]
        if isinstance(row["version_error_message"], str)
        else None,
        page_count=int(row["page_count"]) if row["page_count"] is not None else None,
        chunk_count=int(row["chunk_count"]),
    )
    job = IngestionJob(
        id=UUID(str(row["job_id"])),
        document_id=document.id,
        document_version_id=version.id,
        tenant_id=document.tenant_id,
        knowledge_base_id=document.knowledge_base_id,
        status=JobStatus(str(row["job_status"])),
        current_stage=str(row["current_stage"]),
        error_message=row["job_error_message"]
        if isinstance(row["job_error_message"], str)
        else None,
    )
    return document, version, job


def create_document_ingestion(
    connection: Connection,
    *,
    tenant_id: UUID,
    knowledge_base_id: UUID,
    filename: str,
    content_hash: str,
    size_bytes: int,
    storage_key: str,
) -> tuple[DocumentRecord, DocumentVersion, IngestionJob]:
    document = DocumentRecord(
        id=uuid4(),
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        filename=filename,
        content_hash=content_hash,
        size_bytes=size_bytes,
        mime_type="application/pdf",
    )
    version = DocumentVersion(
        id=uuid4(),
        document_id=document.id,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        version_number=1,
        storage_key=storage_key,
        status=DocumentStatus.QUEUED,
        error_message=None,
        page_count=None,
        chunk_count=0,
    )
    job = IngestionJob(
        id=uuid4(),
        document_id=document.id,
        document_version_id=version.id,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        status=JobStatus.QUEUED,
        current_stage="queued",
        error_message=None,
    )
    connection.execute(
        """
        INSERT INTO document (
            id, tenant_id, knowledge_base_id, filename, content_hash, size_bytes, mime_type
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            document.id,
            document.tenant_id,
            document.knowledge_base_id,
            document.filename,
            document.content_hash,
            document.size_bytes,
            document.mime_type,
        ),
    )
    connection.execute(
        """
        INSERT INTO document_version (
            id, tenant_id, knowledge_base_id, document_id, version_number, storage_key, status,
            embedding_model, chunking_strategy_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            version.id,
            version.tenant_id,
            version.knowledge_base_id,
            version.document_id,
            version.version_number,
            version.storage_key,
            version.status.value,
            EMBEDDING_MODEL,
            CHUNKING_STRATEGY_VERSION,
        ),
    )
    connection.execute(
        """
        INSERT INTO ingestion_job (
            id, tenant_id, knowledge_base_id, document_id, document_version_id, status
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            job.id,
            job.tenant_id,
            job.knowledge_base_id,
            job.document_id,
            job.document_version_id,
            job.status.value,
        ),
    )
    _append_outbox(connection, job, version.storage_key, "ingestion.requested")
    return document, version, job


def _append_outbox(
    connection: Connection,
    job: IngestionJob,
    storage_key: str,
    event_type: str,
) -> None:
    connection.execute(
        """
        INSERT INTO outbox (id, tenant_id, aggregate_id, event_type, payload)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        """,
        (
            uuid4(),
            job.tenant_id,
            job.id,
            event_type,
            Jsonb(
                {
                    "job_id": str(job.id),
                    "tenant_id": str(job.tenant_id),
                    "knowledge_base_id": str(job.knowledge_base_id),
                    "document_id": str(job.document_id),
                    "document_version_id": str(job.document_version_id),
                    "storage_key": storage_key,
                }
            ),
        ),
    )


def list_documents(connection: Connection) -> list[dict[str, Any]]:
    return list(
        connection.execute(
            """
            SELECT d.id, d.knowledge_base_id, d.filename, d.content_hash, d.size_bytes,
                   dv.id AS version_id, dv.status, dv.error_message, dv.created_at,
                   j.id AS ingestion_job_id
            FROM document d
            JOIN LATERAL (
                SELECT * FROM document_version
                WHERE document_id = d.id
                ORDER BY version_number DESC
                LIMIT 1
            ) dv ON true
            JOIN ingestion_job j ON j.document_version_id = dv.id
            WHERE d.deleted_at IS NULL
            ORDER BY d.created_at DESC
            """
        ).fetchall()
    )


def get_document_job(connection: Connection, document_id: UUID) -> IngestionJob | None:
    row = connection.execute(
        """
        SELECT j.id, j.document_id, j.document_version_id, j.tenant_id, j.knowledge_base_id,
               j.status, j.current_stage, j.error_message, j.attempt_count, j.updated_at
        FROM ingestion_job j
        WHERE j.document_id = %s
        ORDER BY j.created_at DESC
        LIMIT 1
        """,
        (document_id,),
    ).fetchone()
    return _job(row) if row else None


def reprocess_document(
    connection: Connection, document_id: UUID
) -> tuple[DocumentVersion, IngestionJob]:
    row = connection.execute(
        """
        SELECT * FROM document_version
        WHERE document_id = %s
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (document_id,),
    ).fetchone()
    if row is None:
        raise LookupError("Document not found")
    previous = _version(row)
    version = DocumentVersion(
        id=uuid4(),
        document_id=previous.document_id,
        tenant_id=previous.tenant_id,
        knowledge_base_id=previous.knowledge_base_id,
        version_number=previous.version_number + 1,
        storage_key=previous.storage_key,
        status=DocumentStatus.QUEUED,
        error_message=None,
        page_count=None,
        chunk_count=0,
    )
    job = IngestionJob(
        id=uuid4(),
        document_id=previous.document_id,
        document_version_id=version.id,
        tenant_id=previous.tenant_id,
        knowledge_base_id=previous.knowledge_base_id,
        status=JobStatus.QUEUED,
        current_stage="queued",
        error_message=None,
    )
    connection.execute(
        """
        INSERT INTO document_version (
            id, tenant_id, knowledge_base_id, document_id, version_number, storage_key, status,
            embedding_model, chunking_strategy_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            version.id,
            version.tenant_id,
            version.knowledge_base_id,
            version.document_id,
            version.version_number,
            version.storage_key,
            version.status.value,
            EMBEDDING_MODEL,
            CHUNKING_STRATEGY_VERSION,
        ),
    )
    connection.execute(
        """
        INSERT INTO ingestion_job (
            id, tenant_id, knowledge_base_id, document_id, document_version_id, status
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            job.id,
            job.tenant_id,
            job.knowledge_base_id,
            job.document_id,
            job.document_version_id,
            job.status.value,
        ),
    )
    _append_outbox(connection, job, version.storage_key, "ingestion.requested")
    return version, job


def soft_delete_document(connection: Connection, document_id: UUID) -> bool:
    row = connection.execute(
        """
        SELECT id, tenant_id, knowledge_base_id
        FROM document
        WHERE id = %s AND deleted_at IS NULL
        FOR UPDATE
        """,
        (document_id,),
    ).fetchone()
    if row is None:
        return False
    result = connection.execute(
        "UPDATE document SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL",
        (document_id,),
    )
    if result.rowcount != 1:
        return False
    connection.execute(
        """
        INSERT INTO outbox (id, tenant_id, aggregate_id, event_type, payload)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        """,
        (
            uuid4(),
            _uuid(row, "tenant_id"),
            document_id,
            "document.delete_requested",
            Jsonb(
                {
                    "tenant_id": str(_uuid(row, "tenant_id")),
                    "knowledge_base_id": str(_uuid(row, "knowledge_base_id")),
                    "document_id": str(document_id),
                }
            ),
        ),
    )
    return True
