"""Tests for the ADR-012 structural versus semantic chunking matrix."""

from __future__ import annotations

import numpy as np
import pytest

from evals.benchmark.chunking_experiment import (
    ChunkingVariant,
    build_chunked_corpus,
    default_chunking_variants,
)
from evals.benchmark.corpus import BenchmarkPage
from evals.benchmark.registry import CANDIDATES
from evals.benchmark.report import chunking_result_validity, render_chunking_markdown_comparison
from evals.benchmark.runner import benchmark_result_identity, make_config


class WordTokenizer:
    def tokenize(self, text: str) -> list[int]:
        return list(range(len(text.split())))


class StaticEmbedder:
    dimension = 2

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return np.ones((len(texts), 2), dtype=np.float32)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return np.ones((len(texts), 2), dtype=np.float32)

    def tokenize(self, text: str) -> list[int]:
        return list(range(len(text.split())))


class FakeDocument:
    def __init__(self, page_content: str) -> None:
        self.page_content = page_content


class FakeSemanticSplitter:
    def create_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, object]],
    ) -> list[FakeDocument]:
        assert metadatas == [{"document": "doc.pdf", "page_number": 3}]
        return [
            FakeDocument("um dois três"),
            FakeDocument("quatro cinco seis sete oito nove dez"),
        ]


class OneSegmentPerPageSplitter:
    def create_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, object]],
    ) -> list[FakeDocument]:
        del metadatas
        return [FakeDocument(texts[0])]


def test_default_matrix_compares_both_strategies_at_three_sizes() -> None:
    variants = default_chunking_variants()

    assert [(variant.strategy, variant.chunk_size) for variant in variants] == [
        ("structural", 256),
        ("structural", 512),
        ("structural", 1024),
        ("semantic", 256),
        ("semantic", 512),
        ("semantic", 1024),
    ]
    assert [variant.overlap for variant in variants] == [32, 64, 128, 32, 64, 128]
    assert len({variant.strategy_version for variant in variants}) == 6


def test_semantic_chunking_preserves_page_and_caps_oversized_segments() -> None:
    variant = ChunkingVariant(strategy="semantic", chunk_size=5, overlap=1)
    page = BenchmarkPage(
        document="doc.pdf",
        page_number=3,
        text="conteúdo narrativo",
        source_path="support/doc.pdf",
        source_page_number=3,
    )

    result = build_chunked_corpus(
        [page],
        variant=variant,
        tokenizer=WordTokenizer(),
        embedder=StaticEmbedder(),
        semantic_splitter_factory=lambda _embeddings: FakeSemanticSplitter(),
    )

    assert [chunk.page_number for chunk in result.chunks] == [3, 3, 3]
    assert [chunk.position for chunk in result.chunks] == [0, 1, 2]
    assert [chunk.token_count for chunk in result.chunks] == [4, 5, 4]
    assert result.documents == {"doc.pdf": {"pages": 1, "chunks": 3}}
    assert result.strategy_version == "semantic-percentile-v1-t5-o1"


def test_semantic_boundaries_are_coalesced_to_target_size_across_pages() -> None:
    variant = ChunkingVariant(strategy="semantic", chunk_size=5, overlap=1)
    pages = [
        BenchmarkPage("doc.pdf", 1, "um dois", "doc.pdf", 1),
        BenchmarkPage("doc.pdf", 2, "três quatro", "doc.pdf", 2),
    ]

    result = build_chunked_corpus(
        pages,
        variant=variant,
        tokenizer=WordTokenizer(),
        embedder=StaticEmbedder(),
        semantic_splitter_factory=lambda _embeddings: OneSegmentPerPageSplitter(),
    )

    assert [chunk.text for chunk in result.chunks] == ["um dois três quatro"]
    assert result.chunks[0].page_numbers == (1, 2)


def test_chunking_variant_is_persisted_in_benchmark_config(tmp_path) -> None:
    variant = ChunkingVariant(strategy="semantic", chunk_size=256, overlap=32)

    config = make_config(
        candidate=CANDIDATES["e5-small"],
        dataset_path=tmp_path / "golden.jsonl",
        manifest_path=tmp_path / "manifest.json",
        output_path=tmp_path / "result.json",
        device="cpu",
        offline=True,
        max_pages_per_document=None,
        max_items=None,
        publish_requested=False,
        chunking_variant=variant,
    )

    assert config.chunking_strategy == "semantic"
    assert config.chunking_strategy_version == "semantic-percentile-v1-t256-o32"
    assert config.chunk_size == 256
    assert config.chunk_overlap == 32
    assert benchmark_result_identity(config) == (
        "adr-012-benchmark-result-v1",
        "ADR-012",
        "chunking",
    )


def test_chunking_report_identifies_each_strategy_version() -> None:
    def result(strategy: str, version: str, recall: float) -> dict[str, object]:
        return {
            "schema_version": "adr-012-benchmark-result-v1",
            "adr": "ADR-012",
            "experiment_type": "chunking",
            "model": {"alias": "e5-small", "model_name": "intfloat/multilingual-e5-small"},
            "config": {
                "chunking_strategy": strategy,
                "chunking_strategy_version": version,
                "chunk_tokenizer_name": "intfloat/multilingual-e5-small",
                "max_items": None,
                "max_pages_per_document": None,
                "device": "cpu",
            },
            "hashes": {
                "dataset_sha256": "dataset",
                "manifest_sha256": "manifest",
                "corpus_sha256": "corpus",
                "document_hashes_sha256": "documents",
            },
            "publishability": {"publishable": False, "label": "PROVISIONAL"},
            "metrics": {
                "recall_at": {"10": recall},
                "mrr_at_10": recall,
                "ndcg_at_10": recall,
                "query_latency_ms": {"p95": 10.0},
            },
            "timings": {"chunking_ms": 2.0, "corpus_encoding_ms": 3.0},
            "corpus": {"chunk_count": 4},
        }

    markdown = render_chunking_markdown_comparison(
        [
            result("semantic", "semantic-percentile-v1-t256-o32", 0.8),
            result("structural", "structural-v1-t256-o32", 0.7),
        ]
    )

    assert "ADR-012 Chunking Benchmark Comparison — PROVISIONAL" in markdown
    assert "semantic-percentile-v1-t256-o32" in markdown
    assert "structural-v1-t256-o32" in markdown


def test_chunking_report_rejects_different_embedding_models() -> None:
    shared = {
        "schema_version": "adr-012-benchmark-result-v1",
        "adr": "ADR-012",
        "experiment_type": "chunking",
        "config": {
            "chunking_strategy": "structural",
            "chunking_strategy_version": "structural-v1-t256-o32",
            "chunk_size": 256,
            "chunk_tokenizer_name": "intfloat/multilingual-e5-small",
            "max_items": None,
            "max_pages_per_document": None,
            "device": "cpu",
        },
        "hashes": {
            "dataset_sha256": "dataset",
            "manifest_sha256": "manifest",
            "corpus_sha256": "corpus",
            "document_hashes_sha256": "documents",
        },
        "publishability": {"publishable": False},
        "metrics": {},
        "timings": {},
        "corpus": {},
    }
    first = {**shared, "model": {"alias": "e5-small", "model_name": "e5-small"}}
    second = {**shared, "model": {"alias": "bge-m3", "model_name": "bge-m3"}}

    with pytest.raises(ValueError, match="model_name"):
        render_chunking_markdown_comparison([first, second])


def test_chunking_result_marks_variant_above_model_limit_invalid() -> None:
    result = {
        "model": {"alias": "e5-small"},
        "config": {"chunk_size": 1024},
    }

    assert chunking_result_validity(result) == "INVALID_MODEL_LIMIT"
