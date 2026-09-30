"""Tenant-filtered Qdrant retrieval for the tutor."""

from __future__ import annotations

from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sentence_transformers import SentenceTransformer

from tutor_ai.chat.domain import RetrievedChunk


class QdrantRetriever:
    """Retrieve only chunks belonging to the authenticated tenant and knowledge base."""

    def __init__(self, url: str, model_name: str, collection: str, limit: int) -> None:
        self._client = QdrantClient(url=url)
        self._model_name = model_name
        self._collection = collection
        self._limit = limit
        self._model: SentenceTransformer | None = None

    def search(
        self, question: str, tenant_id: UUID, knowledge_base_id: UUID
    ) -> list[RetrievedChunk]:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        vector = self._model.encode([f"query: {question}"])[0].tolist()
        points = self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=str(tenant_id))),
                    FieldCondition(
                        key="knowledge_base_id",
                        match=MatchValue(value=str(knowledge_base_id)),
                    ),
                ]
            ),
            limit=self._limit,
        )
        chunks: list[RetrievedChunk] = []
        for point in points:
            payload = point.payload or {}
            if not {"document_id", "document_version_id", "page_number", "text"} <= payload.keys():
                continue
            chunks.append(
                RetrievedChunk(
                    chunk_id=str(point.id),
                    document_id=UUID(str(payload["document_id"])),
                    document_version_id=UUID(str(payload["document_version_id"])),
                    page_number=int(payload["page_number"]),
                    snippet=str(payload["text"]),
                    score=float(point.score),
                )
            )
        return chunks
