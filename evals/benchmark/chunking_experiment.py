"""Reproducible ADR-012 structural versus semantic chunking variants."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol

from evals.benchmark.chunking import (
    CANONICAL_CHUNK_PREFIX,
    ChunkedCorpus,
    ChunkTokenizer,
    chunk_pages,
)
from evals.benchmark.corpus import BenchmarkPage
from evals.benchmark.embeddings import Embedder
from evals.benchmark.retrieval import BenchmarkChunk

ChunkingStrategy = Literal["structural", "semantic"]


class SemanticDocument(Protocol):
    page_content: str


class SemanticSplitter(Protocol):
    def create_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, object]],
    ) -> Sequence[SemanticDocument]: ...


@dataclass(frozen=True)
class ChunkingVariant:
    strategy: ChunkingStrategy
    chunk_size: int
    overlap: int

    def __post_init__(self) -> None:
        if self.strategy not in ("structural", "semantic"):
            raise ValueError(f"unsupported chunking strategy: {self.strategy}")
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        if self.overlap < 0 or self.overlap >= self.chunk_size:
            raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    @property
    def strategy_version(self) -> str:
        family = "structural-v1" if self.strategy == "structural" else "semantic-percentile-v1"
        return f"{family}-t{self.chunk_size}-o{self.overlap}"


@dataclass(frozen=True)
class ChunkingExperimentCorpus:
    chunks: list[BenchmarkChunk]
    chunking_ms: float
    documents: dict[str, dict[str, int]]
    strategy_version: str


class _LangChainEmbeddingsAdapter:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embedder.embed_passages(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._embedder.embed_queries([text])[0].tolist()


def default_chunking_variants() -> list[ChunkingVariant]:
    sizes_and_overlaps = ((256, 32), (512, 64), (1024, 128))
    return [
        ChunkingVariant(strategy=strategy, chunk_size=size, overlap=overlap)
        for strategy in ("structural", "semantic")
        for size, overlap in sizes_and_overlaps
    ]


def _default_semantic_splitter_factory(embeddings: Any) -> SemanticSplitter:
    from langchain_experimental.text_splitter import SemanticChunker

    return SemanticChunker(
        embeddings,
        breakpoint_threshold_type="percentile",
    )


def _semantic_chunks(
    pages: list[BenchmarkPage],
    *,
    variant: ChunkingVariant,
    tokenizer: ChunkTokenizer,
    embedder: Embedder,
    semantic_splitter_factory: Callable[[Any], SemanticSplitter] | None,
) -> ChunkedCorpus:
    from mentora_worker.chunking.structural import StructuralChunker
    from mentora_worker.extraction.docling_adapter import ExtractedDocument, PageBlock

    factory = semantic_splitter_factory or _default_semantic_splitter_factory
    splitter = factory(_LangChainEmbeddingsAdapter(embedder))
    chunks: list[BenchmarkChunk] = []
    document_stats: dict[str, dict[str, int]] = {}
    pages_by_document: dict[str, list[BenchmarkPage]] = {}
    for page in pages:
        pages_by_document.setdefault(page.document, []).append(page)

    for document_name in sorted(pages_by_document):
        document_pages = sorted(
            pages_by_document[document_name],
            key=lambda page: page.page_number,
        )
        semantic_pages: list[PageBlock] = []
        for page in document_pages:
            semantic_documents = splitter.create_documents(
                [page.text],
                metadatas=[{"document": page.document, "page_number": page.page_number}],
            )
            segments = [
                " ".join(semantic_document.page_content.split())
                for semantic_document in semantic_documents
                if semantic_document.page_content.strip()
            ]
            if segments:
                semantic_pages.append(
                    PageBlock(page_number=page.page_number, text="\n".join(segments))
                )
        bounded = StructuralChunker(
            chunk_size=variant.chunk_size,
            overlap=variant.overlap,
            encode_fn=tokenizer.tokenize,
            token_count_prefix=CANONICAL_CHUNK_PREFIX,
        ).chunk(ExtractedDocument(pages=semantic_pages, title=document_name))
        for position, bounded_chunk in enumerate(bounded):
            chunks.append(
                BenchmarkChunk(
                    chunk_id=f"{document_name}:{bounded_chunk.page_number}:{position}",
                    document=document_name,
                    page_number=bounded_chunk.page_number,
                    position=position,
                    text=bounded_chunk.text,
                    content_hash=hashlib.sha256(bounded_chunk.text.encode()).hexdigest(),
                    token_count=bounded_chunk.token_count,
                    page_numbers=bounded_chunk.page_numbers,
                )
            )
        document_stats[document_name] = {
            "pages": len(document_pages),
            "chunks": len(bounded),
        }
    return ChunkedCorpus(chunks=chunks, chunking_ms=0.0, documents=document_stats)


def build_chunked_corpus(
    pages: list[BenchmarkPage],
    *,
    variant: ChunkingVariant,
    tokenizer: ChunkTokenizer,
    embedder: Embedder,
    semantic_splitter_factory: Callable[[Any], SemanticSplitter] | None = None,
) -> ChunkingExperimentCorpus:
    started = time.perf_counter()
    if variant.strategy == "structural":
        chunked = chunk_pages(
            pages,
            encode_fn=tokenizer.tokenize,
            chunk_size=variant.chunk_size,
            overlap=variant.overlap,
        )
    else:
        chunked = _semantic_chunks(
            pages,
            variant=variant,
            tokenizer=tokenizer,
            embedder=embedder,
            semantic_splitter_factory=semantic_splitter_factory,
        )
    return ChunkingExperimentCorpus(
        chunks=chunked.chunks,
        chunking_ms=(time.perf_counter() - started) * 1000,
        documents=chunked.documents,
        strategy_version=variant.strategy_version,
    )
