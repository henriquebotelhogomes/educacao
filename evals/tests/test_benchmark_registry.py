"""Unit tests for ADR-018 embedding candidate registry and prefixes."""

from __future__ import annotations

import numpy as np

from evals.benchmark import chunking
from evals.benchmark.embeddings import SentenceTransformerAdapter, normalize_embeddings
from evals.benchmark.registry import CANDIDATES, EmbeddingCandidate
from evals.benchmark.retrieval import BenchmarkChunk
from evals.benchmark.runner import assess_embedding_inputs


def test_registry_contains_exact_adr_018_candidates_and_dimensions() -> None:
    assert list(CANDIDATES) == ["minilm-l6-v2", "e5-small", "e5-base", "bge-m3"]
    assert CANDIDATES["minilm-l6-v2"].model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert CANDIDATES["minilm-l6-v2"].dimension == 384
    assert CANDIDATES["e5-small"].model_name == "intfloat/multilingual-e5-small"
    assert CANDIDATES["e5-small"].dimension == 384
    assert CANDIDATES["e5-small"].max_sequence_tokens == 512
    assert CANDIDATES["e5-base"].model_name == "intfloat/multilingual-e5-base"
    assert CANDIDATES["e5-base"].dimension == 768
    assert CANDIDATES["bge-m3"].model_name == "BAAI/bge-m3"
    assert CANDIDATES["bge-m3"].dimension == 1024
    assert CANDIDATES["bge-m3"].max_sequence_tokens == 8192


def test_e5_models_prefix_queries_and_passages() -> None:
    adapter = SentenceTransformerAdapter(CANDIDATES["e5-small"], device="cpu", offline=True)

    assert adapter.prepare_queries(["Como plantar milho?"]) == ["query: Como plantar milho?"]
    assert adapter.prepare_passages(["Milho precisa de solo fértil."]) == [
        "passage: Milho precisa de solo fértil."
    ]


def test_non_e5_models_do_not_receive_e5_prefixes() -> None:
    adapter = SentenceTransformerAdapter(CANDIDATES["bge-m3"], device="cpu", offline=True)

    assert adapter.prepare_queries(["Como plantar milho?"]) == ["Como plantar milho?"]
    assert adapter.prepare_passages(["Milho precisa de solo fértil."]) == [
        "Milho precisa de solo fértil."
    ]


def test_chunking_uses_the_production_e5_tokenizer_independently_of_candidate() -> None:
    assert hasattr(chunking, "CanonicalChunkTokenizer")
    loaded: list[str] = []

    class Tokenizer:
        def encode(self, text: str, *, verbose: bool) -> list[int]:
            assert verbose is False
            return list(range(len(text.split())))

    def tokenizer_factory(model_name: str) -> Tokenizer:
        loaded.append(model_name)
        return Tokenizer()

    tokenizer = chunking.CanonicalChunkTokenizer(tokenizer_factory=tokenizer_factory)

    assert chunking.CANONICAL_CHUNK_TOKENIZER == "intfloat/multilingual-e5-small"
    assert tokenizer.tokenize("um dois três") == [0, 1, 2]
    assert loaded == [chunking.CANONICAL_CHUNK_TOKENIZER]


def test_embeddings_are_l2_normalized_even_when_model_is_not() -> None:
    vectors = np.array([[3.0, 4.0], [10.0, 0.0]], dtype=np.float32)

    normalized = normalize_embeddings(vectors)

    assert np.allclose(np.linalg.norm(normalized, axis=1), np.array([1.0, 1.0]))
    assert np.allclose(normalized[0], np.array([0.6, 0.8], dtype=np.float32))


def test_embedding_input_assessment_counts_prepared_text_truncation() -> None:
    class PrefixEmbedder:
        def prepare_passages(self, texts: list[str]) -> list[str]:
            return [f"passage: {text}" for text in texts]

        def tokenize(self, text: str) -> list[int]:
            return list(range(len(text.split())))

    candidate = EmbeddingCandidate("test", "test/model", 2, "test", 3)
    chunks = [
        BenchmarkChunk("a", "doc.pdf", 1, 0, "one", "a", 1),
        BenchmarkChunk("b", "doc.pdf", 1, 1, "one two three", "b", 3),
    ]

    summary = assess_embedding_inputs(
        chunks=chunks,
        embedder=PrefixEmbedder(),
        candidate=candidate,
    )

    assert summary.max_sequence_tokens == 3
    assert summary.max_prepared_tokens == 4
    assert summary.truncated_chunk_count == 1
    assert summary.valid is False
