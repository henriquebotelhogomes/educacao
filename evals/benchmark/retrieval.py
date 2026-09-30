"""In-memory cosine retrieval for ADR-018 benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from evals.benchmark.embeddings import normalize_embeddings


@dataclass(frozen=True)
class BenchmarkChunk:
    chunk_id: str
    document: str
    page_number: int
    position: int
    text: str
    content_hash: str
    token_count: int
    page_numbers: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.document:
            raise ValueError("chunk document must not be empty")
        if self.page_number < 1:
            raise ValueError("chunk page_number must be >= 1")
        if not self.page_numbers:
            object.__setattr__(self, "page_numbers", (self.page_number,))
        if any(page < 1 for page in self.page_numbers):
            raise ValueError("chunk page_numbers must contain only values >= 1")


@dataclass(frozen=True)
class SearchResult:
    chunk: BenchmarkChunk
    score: float
    rank: int


class InMemoryCosineIndex:
    """Small deterministic cosine index over normalized in-memory vectors."""

    def __init__(self, chunks: list[BenchmarkChunk], embeddings: np.ndarray) -> None:
        vectors = normalize_embeddings(np.asarray(embeddings, dtype=np.float32))
        if len(chunks) != vectors.shape[0]:
            raise ValueError(
                f"chunk/vector count mismatch: {len(chunks)} chunks, {vectors.shape[0]} vectors"
            )
        if vectors.ndim != 2:
            raise ValueError("embeddings must be a 2D array")
        self.chunks = list(chunks)
        self.embeddings = vectors

    def search(self, query_vector: np.ndarray, *, top_k: int = 10) -> list[SearchResult]:
        if top_k < 1 or not self.chunks:
            return []
        query = normalize_embeddings(np.asarray(query_vector, dtype=np.float32))[0]
        if query.shape[0] != self.embeddings.shape[1]:
            raise ValueError(
                f"query dimension {query.shape[0]} does not match index dimension "
                f"{self.embeddings.shape[1]}"
            )
        scores = self.embeddings @ query
        ordered = sorted(
            range(len(self.chunks)),
            key=lambda idx: (-float(scores[idx]), self.chunks[idx].chunk_id),
        )[:top_k]
        return [
            SearchResult(chunk=self.chunks[idx], score=float(scores[idx]), rank=rank)
            for rank, idx in enumerate(ordered, start=1)
        ]
