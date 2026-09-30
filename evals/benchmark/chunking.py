"""Structural chunking adapter for ADR-018 benchmarks."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from evals.benchmark.corpus import BenchmarkPage
from evals.benchmark.retrieval import BenchmarkChunk

CANONICAL_CHUNK_TOKENIZER = "intfloat/multilingual-e5-small"
CANONICAL_CHUNK_PREFIX = "passage: "


class ChunkTokenizer(Protocol):
    def tokenize(self, text: str) -> list[int]: ...


class CanonicalChunkTokenizer:
    """Keep ADR-018 chunk boundaries fixed while embedding models vary."""

    def __init__(
        self,
        tokenizer_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self._tokenizer_factory = tokenizer_factory
        self._tokenizer: Any | None = None

    def tokenize(self, text: str) -> list[int]:
        if self._tokenizer is None:
            if self._tokenizer_factory is not None:
                self._tokenizer = self._tokenizer_factory(CANONICAL_CHUNK_TOKENIZER)
            else:
                from transformers import AutoTokenizer

                self._tokenizer = AutoTokenizer.from_pretrained(CANONICAL_CHUNK_TOKENIZER)
        return list(self._tokenizer.encode(text, verbose=False))


@dataclass(frozen=True)
class ChunkedCorpus:
    chunks: list[BenchmarkChunk]
    chunking_ms: float
    documents: dict[str, dict[str, int]]


def chunk_pages(
    pages: list[BenchmarkPage],
    *,
    encode_fn: Callable[[str], list[int]],
    chunk_size: int = 512,
    overlap: int = 64,
) -> ChunkedCorpus:
    """Chunk pages with the production StructuralChunker algorithm."""
    started = time.perf_counter()
    from mentora_worker.chunking.structural import StructuralChunker
    from mentora_worker.extraction.docling_adapter import ExtractedDocument, PageBlock

    chunks: list[BenchmarkChunk] = []
    docs: dict[str, list[BenchmarkPage]] = {}
    for page in pages:
        docs.setdefault(page.document, []).append(page)

    document_stats: dict[str, dict[str, int]] = {}
    for document_name in sorted(docs):
        doc_pages = sorted(docs[document_name], key=lambda page: page.page_number)
        extracted = ExtractedDocument(
            pages=[PageBlock(page_number=page.page_number, text=page.text) for page in doc_pages],
            title=document_name,
        )
        produced = StructuralChunker(
            chunk_size=chunk_size,
            overlap=overlap,
            encode_fn=encode_fn,
            token_count_prefix=CANONICAL_CHUNK_PREFIX,
        ).chunk(extracted)
        document_stats[document_name] = {"pages": len(doc_pages), "chunks": len(produced)}
        for chunk in produced:
            chunks.append(
                BenchmarkChunk(
                    chunk_id=f"{document_name}:{chunk.page_number}:{chunk.position}",
                    document=document_name,
                    page_number=chunk.page_number,
                    position=chunk.position,
                    text=chunk.text,
                    content_hash=chunk.content_hash,
                    token_count=chunk.token_count,
                    page_numbers=chunk.page_numbers,
                )
            )

    return ChunkedCorpus(
        chunks=chunks,
        chunking_ms=(time.perf_counter() - started) * 1000,
        documents=document_stats,
    )
