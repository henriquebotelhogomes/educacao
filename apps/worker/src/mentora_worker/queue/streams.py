"""Redis Streams native consumer group — XREADGROUP / XAUTOCLAIM / XACK (ADR-017)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import redis.asyncio
import redis.exceptions

from mentora_worker.config import WorkerSettings
from mentora_worker.queue.messages import DeletionMessage, IngestionMessage, parse_stream_message

logger = logging.getLogger(__name__)


@dataclass
class PendingMessage:
    """A message claimed from the Redis Stream pending-entries list."""

    stream_id: str
    message: IngestionMessage | DeletionMessage
    delivery_count: int


def _decode(value: bytes | str) -> str:
    """Decode bytes to str, pass through str unchanged."""
    return value.decode() if isinstance(value, bytes) else value


def _decode_fields(raw: dict[Any, Any]) -> dict[str, str]:
    """Decode all keys and values in a Redis fields dict to str."""
    return {_decode(k): _decode(v) for k, v in raw.items()}


class RedisStreamConsumer:
    """Native Redis Streams consumer using XREADGROUP / XAUTOCLAIM (ADR-017)."""

    def __init__(self, settings: WorkerSettings, client: redis.asyncio.Redis) -> None:
        self._settings = settings
        self._client = client

    async def ensure_group(self) -> None:
        """Create consumer group with MKSTREAM; silently ignore BUSYGROUP errors."""
        try:
            await self._client.xgroup_create(
                name=self._settings.ingestion_stream,
                groupname=self._settings.ingestion_consumer_group,
                id="0",
                mkstream=True,
            )
            logger.info("Consumer group '%s' created.", self._settings.ingestion_consumer_group)
        except redis.exceptions.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                logger.debug("Consumer group already exists, continuing.")
            else:
                raise

    async def read_new(self) -> list[PendingMessage]:
        """Read new (undelivered) messages via XREADGROUP blocking poll."""
        result = await self._client.xreadgroup(
            groupname=self._settings.ingestion_consumer_group,
            consumername=self._settings.ingestion_consumer_name,
            streams={self._settings.ingestion_stream: ">"},
            count=10,
            block=self._settings.stream_block_ms,
        )
        if not result:
            return []

        messages: list[PendingMessage] = []
        for _stream_name, entries in result:
            for msg_id_raw, fields_raw in entries:
                msg_id = _decode(msg_id_raw)
                fields = _decode_fields(fields_raw)
                try:
                    msg = parse_stream_message(fields)
                    messages.append(PendingMessage(stream_id=msg_id, message=msg, delivery_count=1))
                except Exception:
                    logger.exception("Unparseable stream message %s → DLQ", msg_id)
                    await self.send_to_dlq(msg_id, fields, "parse_error")
        return messages

    async def autoclaim(self) -> list[PendingMessage]:
        """Claim stale PEL messages via XAUTOCLAIM; fetch delivery counts with XPENDING."""
        result = await self._client.xautoclaim(
            name=self._settings.ingestion_stream,
            groupname=self._settings.ingestion_consumer_group,
            consumername=self._settings.ingestion_consumer_name,
            min_idle_time=self._settings.autoclaim_min_idle_ms,
            start_id="0-0",
        )
        # result → [next_id, [[id, {fields}], ...], [deleted_ids]]
        entries = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else []
        if not entries:
            return []

        # Batch-fetch delivery counts for all claimed messages.
        delivery_counts: dict[str, int] = {}
        try:
            pending_list = await self._client.xpending_range(
                name=self._settings.ingestion_stream,
                groupname=self._settings.ingestion_consumer_group,
                min="-",
                max="+",
                count=len(entries) * 2,
                consumername=self._settings.ingestion_consumer_name,
            )
            for p in pending_list:
                mid = _decode(p["message_id"])
                delivery_counts[mid] = int(p["times_delivered"])
        except Exception:
            logger.warning("Could not fetch PEL delivery counts; defaulting to 1.")

        messages: list[PendingMessage] = []
        for entry in entries:
            msg_id_raw, fields_raw = entry[0], entry[1]
            msg_id = _decode(msg_id_raw)
            fields = _decode_fields(fields_raw or {})
            dc = delivery_counts.get(msg_id, 1)
            try:
                msg = parse_stream_message(fields)
                messages.append(PendingMessage(stream_id=msg_id, message=msg, delivery_count=dc))
            except Exception:
                logger.exception("Unparseable autoclaimed message %s → DLQ", msg_id)
                await self.send_to_dlq(msg_id, fields, "parse_error")
        return messages

    async def ack(self, stream_id: str) -> None:
        """Acknowledge a message — removes it from the pending-entries list."""
        await self._client.xack(
            self._settings.ingestion_stream,
            self._settings.ingestion_consumer_group,
            stream_id,
        )

    async def send_to_dlq(self, stream_id: str, message: dict[str, str], reason: str) -> None:
        """XADD to the DLQ stream then ACK the original message."""
        dlq_fields: dict[Any, Any] = {
            "original_stream_id": stream_id,
            "reason": reason,
            **message,
        }
        await self._client.xadd(self._settings.ingestion_dlq_stream, dlq_fields)
        await self.ack(stream_id)
        logger.warning("Message %s → DLQ (%s)", stream_id, reason)
