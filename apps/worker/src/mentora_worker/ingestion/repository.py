"""Idempotent ingestion status management — Postgres helpers (ADR-005)."""

from __future__ import annotations

from enum import Enum
from uuid import UUID

import psycopg

from mentora_worker.config import WorkerSettings


class IngestionStatus(str, Enum):
    """Valid states for an ingestion job (matches the DB check constraint)."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


def db_url(settings: WorkerSettings) -> str:
    """Convert the SQLAlchemy DSN to the raw psycopg connection format."""
    return str(settings.database_url).replace("postgresql+psycopg://", "postgresql://", 1)


def claim_for_processing(
    conn: psycopg.Connection,
    tenant_id: UUID,
    job_id: UUID,
    document_version_id: UUID,
    stale_after_ms: int = 60_000,
) -> bool:
    """Claim retryable work without reactivating terminal or actively processed jobs."""
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (str(tenant_id),))
        cur.execute(
            """
            UPDATE ingestion_job
               SET status = 'PROCESSING',
                   current_stage = 'processing',
                   attempt_count = attempt_count + 1,
                   error_message = NULL,
                   updated_at = NOW()
             WHERE id = %s
               AND document_version_id = %s
               AND (
                   status = 'QUEUED'
                   OR status = 'FAILED'
                   OR (
                       status = 'PROCESSING'
                       AND updated_at < NOW() - (%s * INTERVAL '1 millisecond')
                   )
               )
            """,
            (str(job_id), str(document_version_id), stale_after_ms),
        )
        claimed = cur.rowcount == 1
        if claimed:
            cur.execute(
                """
                UPDATE document_version
                   SET status = 'PROCESSING',
                       error_message = NULL
                 WHERE id = %s
                   AND status IN ('QUEUED', 'FAILED', 'PROCESSING')
                """,
                (str(document_version_id),),
            )
    conn.commit()
    return claimed


def set_status(
    conn: psycopg.Connection,
    tenant_id: UUID,
    job_id: UUID,
    document_version_id: UUID,
    status: IngestionStatus,
    error_message: str | None = None,
) -> None:
    """Update both status models atomically under the message tenant RLS context."""
    job_status = {
        IngestionStatus.QUEUED: "QUEUED",
        IngestionStatus.PROCESSING: "PROCESSING",
        IngestionStatus.INDEXED: "COMPLETED",
        IngestionStatus.FAILED: "FAILED",
        IngestionStatus.QUARANTINED: "QUARANTINED",
    }[status]
    stage = {
        IngestionStatus.QUEUED: "queued",
        IngestionStatus.PROCESSING: "processing",
        IngestionStatus.INDEXED: "completed",
        IngestionStatus.FAILED: "failed",
        IngestionStatus.QUARANTINED: "quarantined",
    }[status]
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (str(tenant_id),))
        cur.execute(
            """
            UPDATE ingestion_job
               SET status        = %s,
                   current_stage = %s,
                   attempt_count = CASE
                       WHEN %s = 'PROCESSING' AND status != 'PROCESSING'
                       THEN attempt_count + 1
                       ELSE attempt_count
                   END,
                   updated_at    = NOW(),
                   error_message = COALESCE(%s, error_message)
             WHERE id = %s
               AND status != %s
            """,
            (job_status, stage, job_status, error_message, str(job_id), job_status),
        )
        cur.execute(
            """
            UPDATE document_version
               SET status        = %s,
                   error_message = COALESCE(%s, error_message),
                   indexed_at    = CASE WHEN %s = 'INDEXED' THEN NOW() ELSE indexed_at END
             WHERE id = %s
            """,
            (status.value, error_message, status.value, str(document_version_id)),
        )
    conn.commit()


def complete_indexing(
    conn: psycopg.Connection,
    tenant_id: UUID,
    document_version_id: UUID,
    page_count: int,
    chunk_count: int,
) -> None:
    """Persist index metadata and supersede a prior active version only after success."""
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (str(tenant_id),))
        cur.execute(
            """
            UPDATE document_version
               SET page_count = %s,
                   chunk_count = %s,
                   indexed_at = NOW()
             WHERE id = %s
            """,
            (page_count, chunk_count, str(document_version_id)),
        )
        cur.execute(
            """
            UPDATE document_version
               SET status = 'SUPERSEDED'
             WHERE document_id = (
                       SELECT document_id FROM document_version WHERE id = %s
                   )
               AND id != %s
               AND status = 'INDEXED'
            """,
            (str(document_version_id), str(document_version_id)),
        )
    conn.commit()
