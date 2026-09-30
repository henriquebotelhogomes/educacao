"""Outbox dispatcher: polls Postgres for unpublished events, XADDs to Redis Streams (ADR-017)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import psycopg
import redis.asyncio

from mentora_worker.config import WorkerSettings

logger = logging.getLogger(__name__)


def _pg_url(settings: WorkerSettings) -> str:
    """Convert SQLAlchemy DSN to raw psycopg connection string."""
    return str(settings.database_url).replace("postgresql+psycopg://", "postgresql://", 1)


def _fetch_pending_outbox(settings: WorkerSettings) -> list[dict[str, Any]]:
    """Fetch unpublished outbox rows with SKIP LOCKED (sync psycopg).

    NOTE: The FOR UPDATE lock is released on commit before XADD is called.
    For single-worker deployments this causes no race; multi-worker setups
    would need a held connection or advisory-lock strategy.
    """
    url = _pg_url(settings)
    rows: list[dict[str, Any]] = []
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.worker', 'true', true)")
            cur.execute(
                """
                SELECT id, event_type, payload
                FROM outbox
                WHERE published_at IS NULL
                ORDER BY created_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (settings.outbox_batch_size,),
            )
            for row in cur.fetchall():
                rows.append({"id": row[0], "event_type": row[1], "payload": row[2]})
        conn.commit()
    return rows


def _mark_published(settings: WorkerSettings, ids: list[Any]) -> None:
    """Set published_at=NOW() for the given outbox row IDs (sync psycopg)."""
    if not ids:
        return
    url = _pg_url(settings)
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.worker', 'true', true)")
            cur.execute(
                "UPDATE outbox SET published_at = NOW() WHERE id = ANY(%s)",
                (ids,),
            )
        conn.commit()


async def dispatch_outbox_batch(
    settings: WorkerSettings,
    redis_client: redis.asyncio.Redis,
) -> int:
    """Fetch pending outbox rows, XADD each to Redis, mark published.

    Returns the number of events dispatched.
    """
    rows: list[dict[str, Any]] = await asyncio.to_thread(_fetch_pending_outbox, settings)
    if not rows:
        return 0

    ids_to_mark: list[Any] = []
    published = 0

    for row in rows:
        if row["event_type"] not in {"ingestion.requested", "document.delete_requested"}:
            continue
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)

        fields: dict[Any, Any] = {
            "event_type": str(row["event_type"]),
            "job_id": str(payload.get("job_id", "")),
            "document_id": str(payload.get("document_id", "")),
            "document_version_id": str(payload.get("document_version_id", "")),
            "tenant_id": str(payload.get("tenant_id", "")),
            "knowledge_base_id": str(payload.get("knowledge_base_id", "")),
            "storage_key": str(payload.get("storage_key", "")),
        }
        await redis_client.xadd(settings.ingestion_stream, fields)
        ids_to_mark.append(row["id"])
        published += 1

    if ids_to_mark:
        await asyncio.to_thread(_mark_published, settings, ids_to_mark)

    return published


async def run_outbox_dispatcher(
    settings: WorkerSettings,
    redis_client: redis.asyncio.Redis,
    stop_event: asyncio.Event,
) -> None:
    """Poll the outbox table and dispatch events to Redis until stop_event is set."""
    logger.info(
        "Outbox dispatcher started (poll interval=%.1fs).", settings.outbox_poll_interval_seconds
    )
    while not stop_event.is_set():
        try:
            count = await dispatch_outbox_batch(settings, redis_client)
            if count > 0:
                logger.info("Outbox: dispatched %d event(s) to stream.", count)
        except Exception:
            logger.exception("Outbox dispatcher error.")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.outbox_poll_interval_seconds)
            break  # stop_event was set within the timeout window
        except asyncio.TimeoutError:
            pass  # normal poll cycle

    logger.info("Outbox dispatcher stopped.")
