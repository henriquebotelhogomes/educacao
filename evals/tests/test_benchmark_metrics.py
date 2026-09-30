"""Unit tests for ADR-018 retrieval metrics and unanswerable calibration data."""

from __future__ import annotations

import numpy as np
import pytest

from evals.benchmark.evaluator import evaluate_retrieval
from evals.benchmark.retrieval import BenchmarkChunk, InMemoryCosineIndex
from evals.schema import Difficulty, GoldenItem, ItemType, ReviewStatus


class StaticEmbedder:
    dimension = 2

    def __init__(self, query_vectors: dict[str, list[float]]) -> None:
        self.query_vectors = query_vectors

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return np.array([self.query_vectors[text] for text in texts], dtype=np.float32)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError

    def tokenize(self, text: str) -> list[int]:
        return list(range(len(text.split())))


def _item(
    *,
    item_id: str,
    pergunta: str,
    documento: str,
    paginas: list[int],
    tipo: ItemType = ItemType.ANSWERABLE,
) -> GoldenItem:
    return GoldenItem(
        id=item_id,
        pergunta=pergunta,
        resposta_referencia=None if tipo == ItemType.UNANSWERABLE else "resposta",
        documento=documento,
        paginas_esperadas=paginas,
        evidence_quotes=[] if tipo == ItemType.UNANSWERABLE else ["trecho verificado"],
        tipo=tipo,
        dificuldade=Difficulty.FACIL,
        review_status=ReviewStatus.DRAFT,
        notas="fora do corpus" if tipo == ItemType.UNANSWERABLE else None,
    )


def test_metrics_use_document_and_logical_page_intersection() -> None:
    chunks = [
        BenchmarkChunk(
            chunk_id="doc-a:1:0",
            document="doc-a.pdf",
            page_number=1,
            position=0,
            text="conteúdo certo",
            content_hash="a",
            token_count=2,
        ),
        BenchmarkChunk(
            chunk_id="doc-b:1:0",
            document="doc-b.pdf",
            page_number=1,
            position=0,
            text="mesma página lógica, documento errado",
            content_hash="b",
            token_count=2,
        ),
    ]
    index = InMemoryCosineIndex(
        chunks,
        np.array([[1.0, 0.0], [0.9, 0.1]], dtype=np.float32),
    )
    embedder = StaticEmbedder({"q": [1.0, 0.0]})

    summary = evaluate_retrieval(
        items=[_item(item_id="i1", pergunta="q", documento="doc-a.pdf", paginas=[1])],
        index=index,
        embedder=embedder,
    )

    assert summary.evaluated_item_count == 1
    assert summary.recall_at["1"] == pytest.approx(1.0)
    assert summary.precision_at["1"] == pytest.approx(1.0)
    assert summary.mrr_at_10 == pytest.approx(1.0)
    assert summary.ndcg_at_10 == pytest.approx(1.0)


def test_metrics_match_any_contributing_page_of_a_multipage_chunk() -> None:
    chunk = BenchmarkChunk(
        chunk_id="doc-a:1:0",
        document="doc-a.pdf",
        page_number=1,
        position=0,
        text="fim da página um e começo da página dois",
        content_hash="a",
        token_count=9,
        page_numbers=(1, 2),
    )
    index = InMemoryCosineIndex([chunk], np.array([[1.0, 0.0]], dtype=np.float32))

    summary = evaluate_retrieval(
        items=[_item(item_id="i1", pergunta="q", documento="doc-a.pdf", paginas=[1, 2])],
        index=index,
        embedder=StaticEmbedder({"q": [1.0, 0.0]}),
    )

    assert summary.recall_at["1"] == pytest.approx(1.0)
    assert summary.ndcg_at_10 == pytest.approx(1.0)


def test_precision_at_k_uses_available_results_when_index_has_fewer_than_k() -> None:
    chunks = [
        BenchmarkChunk("doc-a:1:0", "doc-a.pdf", 1, 0, "certo", "a", 1),
        BenchmarkChunk("doc-a:2:0", "doc-a.pdf", 2, 0, "errado", "b", 1),
    ]
    index = InMemoryCosineIndex(chunks, np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32))
    embedder = StaticEmbedder({"q": [1.0, 0.0]})

    summary = evaluate_retrieval(
        items=[_item(item_id="i1", pergunta="q", documento="doc-a.pdf", paginas=[1])],
        index=index,
        embedder=embedder,
    )

    assert summary.precision_at["5"] == pytest.approx(0.5)
    assert summary.recall_at["5"] == pytest.approx(1.0)


def test_unanswerable_items_are_excluded_from_metrics_but_record_top_scores() -> None:
    chunks = [BenchmarkChunk("doc-a:1:0", "doc-a.pdf", 1, 0, "texto", "a", 1)]
    index = InMemoryCosineIndex(chunks, np.array([[1.0, 0.0]], dtype=np.float32))
    embedder = StaticEmbedder({"answerable": [1.0, 0.0], "unanswerable": [1.0, 0.0]})

    summary = evaluate_retrieval(
        items=[
            _item(item_id="i1", pergunta="answerable", documento="doc-a.pdf", paginas=[1]),
            _item(
                item_id="i2",
                pergunta="unanswerable",
                documento="doc-a.pdf",
                paginas=[],
                tipo=ItemType.UNANSWERABLE,
            ),
        ],
        index=index,
        embedder=embedder,
    )

    assert summary.evaluated_item_count == 1
    assert summary.unanswerable_item_count == 1
    assert summary.unanswerable_top_scores[0].item_id == "i2"
    assert summary.unanswerable_top_scores[0].top_scores == [pytest.approx(1.0)]
