"""Ingestion pipeline: scan → extract → chunk → embed → index (ADR-005)."""

from __future__ import annotations

import logging

import psycopg

from mentora_worker.chunking.structural import StructuralChunker
from mentora_worker.config import WorkerSettings
from mentora_worker.embeddings.e5_adapter import E5Embedder
from mentora_worker.extraction.docling_adapter import DoclingExtractor
from mentora_worker.ingestion.repository import (
    IngestionStatus,
    claim_for_processing,
    complete_indexing,
    db_url,
    set_status,
)
from mentora_worker.queue.messages import IngestionMessage
from mentora_worker.scanning.content_scan import ContentScanner
from mentora_worker.storage.minio_adapter import MinIOStorage
from mentora_worker.vectorstore.qdrant_adapter import ChunkPoint, QdrantVectorStore

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the full document ingestion flow for a single message.

    All components are dependency-injected so they can be swapped out in tests.
    The ``run`` method is **synchronous** — the async caller wraps it in
    ``asyncio.to_thread``.
    """

    def __init__(
        self,
        settings: WorkerSettings,
        storage: MinIOStorage,
        scanner: ContentScanner,
        extractor: DoclingExtractor,
        chunker: StructuralChunker,
        embedder: E5Embedder,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._scanner = scanner
        self._extractor = extractor
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store

    def run(self, message: IngestionMessage) -> None:
        """Execute the pipeline for *message*, updating job status at each stage.

        States
        ------
        QUEUED → PROCESSING → INDEXED
        QUEUED → PROCESSING → FAILED
        QUEUED → PROCESSING → QUARANTINED
        """
        pg_url = db_url(self._settings)

        with psycopg.connect(pg_url) as conn:
            claimed = claim_for_processing(
                conn,
                message.tenant_id,
                message.job_id,
                message.document_version_id,
                self._settings.autoclaim_min_idle_ms,
            )
            if not claimed:
                logger.info("Ignoring duplicate or terminal ingestion job %s.", message.job_id)
                return

            try:
                self._process(conn, message)
            except Exception as exc:
                logger.exception("Ingestion failed for job %s", message.job_id)
                set_status(
                    conn,
                    message.tenant_id,
                    message.job_id,
                    message.document_version_id,
                    IngestionStatus.FAILED,
                    str(exc),
                )
                raise

    def _process(self, conn: psycopg.Connection, message: IngestionMessage) -> None:
        # 1 — download
        data = self._storage.download(message.storage_key)

        # 2 — content scan (ADR-022)
        scan_result = self._scanner.scan(data)
        if not scan_result.clean:
            logger.warning(
                "Document quarantined (job=%s, reason=%s)", message.job_id, scan_result.reason
            )
            set_status(
                conn,
                message.tenant_id,
                message.job_id,
                message.document_version_id,
                IngestionStatus.QUARANTINED,
                scan_result.reason,
            )
            return

        # 3 — text extraction
        extracted = self._extractor.extract(data)
        if len(extracted.pages) > self._settings.free_document_max_pages:
            set_status(
                conn,
                message.tenant_id,
                message.job_id,
                message.document_version_id,
                IngestionStatus.FAILED,
                f"page_limit_exceeded:{self._settings.free_document_max_pages}",
            )
            return

        # 4 — chunking
        chunks = self._chunker.chunk(extracted)
        if not chunks:
            logger.warning("No chunks produced for job %s", message.job_id)
            set_status(
                conn,
                message.tenant_id,
                message.job_id,
                message.document_version_id,
                IngestionStatus.FAILED,
                "no_chunks",
            )
            return

        # 5 — embeddings (ADR-021: passage prefix applied inside E5Embedder)
        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed_passages(texts)

        # 6 — build Qdrant points
        points = [
            ChunkPoint(
                chunk=c,
                embedding=e,
                document_id=message.document_id,
                document_version_id=message.document_version_id,
                tenant_id=message.tenant_id,
                knowledge_base_id=message.knowledge_base_id,
                model=self._settings.embedding_model,
                model_version=self._settings.embedding_model_version,
                chunking_strategy_version=self._settings.chunking_strategy_version,
            )
            for c, e in zip(chunks, embeddings, strict=True)
        ]

        # 7 — upsert (idempotent via deterministic point IDs)
        self._vector_store.upsert(points)

        # 8 — persist metadata, supersede only a successfully replaced version, then mark indexed.
        complete_indexing(
            conn,
            message.tenant_id,
            message.document_version_id,
            page_count=len(extracted.pages),
            chunk_count=len(chunks),
        )
        set_status(
            conn,
            message.tenant_id,
            message.job_id,
            message.document_version_id,
            IngestionStatus.INDEXED,
        )
        logger.info(
            "Job %s indexed: %d chunks from %d page(s).",
            message.job_id,
            len(chunks),
            len(extracted.pages),
        )
