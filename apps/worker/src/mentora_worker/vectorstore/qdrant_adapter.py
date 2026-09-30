"""Qdrant vector store adapter with deterministic UUID point IDs (ADR-011, ADR-021)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from mentora_worker.chunking.structural import TextChunk

logger = logging.getLogger(__name__)


def collection_name(model: str, version: str) -> str:
    """Derive Qdrant collection name from model identifier and version tag.

    Example: ``("intfloat/multilingual-e5-small", "v1")`` → ``"multilingual-e5-small_v1"``
    """
    return f"{model.split('/')[-1]}_{version}"


def make_point_id(document_version_id: UUID, chunk_index: int) -> str:
    """Deterministic UUID5 point ID — same document version + position = same ID.

    This makes upserts naturally idempotent: re-indexing the same document
    version always produces the same point IDs, so Qdrant upserts are no-ops
    for unchanged chunks.
    """
    return str(uuid.uuid5(document_version_id, str(chunk_index)))


@dataclass
class ChunkPoint:
    """A single vector point ready for upsert into Qdrant."""

    chunk: TextChunk
    embedding: list[float]
    document_id: UUID
    document_version_id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID
    model: str
    model_version: str
    chunking_strategy_version: str


class QdrantVectorStore:
    """Manages a Qdrant collection for a single model+version pair (ADR-011)."""

    def __init__(self, url: str, collection: str, dim: int) -> None:
        self._client = QdrantClient(url=url)
        self._collection = collection
        self._dim = dim

    def ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection '%s' (dim=%d).", self._collection, self._dim)
        else:
            logger.debug("Qdrant collection '%s' already exists.", self._collection)

    def upsert(self, points: list[ChunkPoint]) -> None:
        """Batch-upsert *points* into the collection.

        Each point's ID is derived deterministically from
        ``(document_version_id, chunk.position)`` so that re-indexing the same
        document is naturally idempotent.
        """
        if not points:
            return

        qdrant_points = [
            PointStruct(
                id=make_point_id(p.document_version_id, p.chunk.position),
                vector=p.embedding,
                payload={
                    "tenant_id": str(p.tenant_id),
                    "document_id": str(p.document_id),
                    "document_version_id": str(p.document_version_id),
                    "knowledge_base_id": str(p.knowledge_base_id),
                    "page_number": p.chunk.page_number,
                    "position": p.chunk.position,
                    "content_hash": p.chunk.content_hash,
                    "model": p.model,
                    "model_version": p.model_version,
                    "chunking_strategy_version": p.chunking_strategy_version,
                    "text": p.chunk.text,
                },
            )
            for p in points
        ]

        self._client.upsert(collection_name=self._collection, points=qdrant_points)
        logger.debug("Upserted %d points into '%s'.", len(qdrant_points), self._collection)

    def delete_document(self, tenant_id: UUID, document_id: UUID) -> None:
        """Delete only points that match both server-derived tenant and document IDs."""
        selector = FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=str(tenant_id))),
                    FieldCondition(key="document_id", match=MatchValue(value=str(document_id))),
                ]
            )
        )
        self._client.delete(collection_name=self._collection, points_selector=selector)
