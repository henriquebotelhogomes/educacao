"""Marco 2 worker: Redis Streams consumer + outbox dispatcher."""

from __future__ import annotations

import asyncio
import logging
import signal

import redis.asyncio

from mentora_worker.chunking.structural import StructuralChunker
from mentora_worker.config import get_settings
from mentora_worker.embeddings.e5_adapter import E5Embedder
from mentora_worker.extraction.docling_adapter import DoclingExtractor
from mentora_worker.ingestion.pipeline import IngestionPipeline
from mentora_worker.queue.messages import DeletionMessage
from mentora_worker.queue.outbox import run_outbox_dispatcher
from mentora_worker.queue.streams import PendingMessage, RedisStreamConsumer
from mentora_worker.scanning.content_scan import ContentScanner
from mentora_worker.storage.minio_adapter import MinIOStorage
from mentora_worker.vectorstore.qdrant_adapter import QdrantVectorStore, collection_name

logger = logging.getLogger(__name__)


async def run() -> None:
    """Full ingestion worker: outbox dispatcher + Redis Streams consumer loop."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("worker.started service=%s env=%s", settings.service_name, settings.environment)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_: stop_event.set())

    redis_client: redis.asyncio.Redis = redis.asyncio.from_url(
        str(settings.redis_url), decode_responses=False
    )

    # Build pipeline components once — reused for every message.
    storage = MinIOStorage(settings)
    scanner = ContentScanner(settings.environment)
    extractor = DoclingExtractor()
    chunker = StructuralChunker(
        chunk_size=settings.chunk_size_tokens,
        overlap=settings.chunk_overlap_tokens,
        token_count_prefix="passage: ",
    )
    embedder = E5Embedder(
        model_name=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
    )
    col = collection_name(settings.embedding_model, settings.embedding_model_version)
    vector_store = QdrantVectorStore(
        url=str(settings.qdrant_url),
        collection=col,
        dim=settings.embedding_dim,
    )
    vector_store.ensure_collection()
    logger.info("Qdrant collection '%s' ready.", col)

    pipeline = IngestionPipeline(
        settings=settings,
        storage=storage,
        scanner=scanner,
        extractor=extractor,
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
    )

    consumer = RedisStreamConsumer(settings, redis_client)
    await consumer.ensure_group()

    outbox_task = asyncio.create_task(
        run_outbox_dispatcher(settings, redis_client, stop_event),
        name="outbox-dispatcher",
    )

    async def _process(pending: PendingMessage) -> None:
        if pending.delivery_count > settings.stream_max_retries:
            logger.warning(
                "Message %s exceeded max retries (%d) → DLQ",
                pending.stream_id,
                settings.stream_max_retries,
            )
            await consumer.send_to_dlq(pending.stream_id, {}, "max_retries_exceeded")
            return
        try:
            if isinstance(pending.message, DeletionMessage):
                await asyncio.to_thread(
                    vector_store.delete_document,
                    pending.message.tenant_id,
                    pending.message.document_id,
                )
            else:
                await asyncio.to_thread(pipeline.run, pending.message)
            await consumer.ack(pending.stream_id)
            logger.info("Message %s processed successfully.", pending.stream_id)
        except Exception:
            logger.exception("Message %s failed; leaving in PEL for retry.", pending.stream_id)

    logger.info("Ingestion loop started.")
    while not stop_event.is_set():
        # Re-claim any stale messages first (idle > autoclaim_min_idle_ms).
        for stale in await consumer.autoclaim():
            await _process(stale)

        # Then read new messages (blocking up to stream_block_ms).
        for msg in await consumer.read_new():
            await _process(msg)

    logger.info("Shutdown signal received.")
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass

    await redis_client.aclose()
    logger.info("worker.stopped")


def main() -> None:
    """Entry point for the Marco 2 worker process."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
