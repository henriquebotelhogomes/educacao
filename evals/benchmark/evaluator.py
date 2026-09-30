"""Retrieval metrics for ADR-018 embedding benchmarks."""

from __future__ import annotations

import math
import time
from typing import Iterable

from evals.benchmark.embeddings import Embedder
from evals.benchmark.retrieval import InMemoryCosineIndex, SearchResult
from evals.benchmark.schemas import LatencySummary, RetrievalSummary, UnanswerableTopScores
from evals.schema import GoldenItem, ItemType

KS = (1, 3, 5, 10)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100) * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[int(rank)]
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def latency_summary(values: list[float]) -> LatencySummary:
    return LatencySummary(p50=percentile(values, 50), p95=percentile(values, 95))


def _is_relevant(result: SearchResult, item: GoldenItem, expected_pages: set[int]) -> bool:
    return result.chunk.document == item.documento and bool(
        set(result.chunk.page_numbers) & expected_pages
    )


def _page_relevance_gains(results: Iterable[SearchResult], item: GoldenItem) -> list[int]:
    expected_pages = set(item.paginas_esperadas)
    seen_pages: set[int] = set()
    gains: list[int] = []
    for result in results:
        matching_pages = set(result.chunk.page_numbers) & expected_pages
        newly_covered = (
            matching_pages - seen_pages if result.chunk.document == item.documento else set()
        )
        gains.append(len(newly_covered))
        seen_pages.update(newly_covered)
    return gains


def _page_relevance_flags(results: Iterable[SearchResult], item: GoldenItem) -> list[int]:
    return [1 if gain else 0 for gain in _page_relevance_gains(results, item)]


def _ndcg_at_10(results: list[SearchResult], item: GoldenItem) -> float:
    gains = _page_relevance_gains(results[:10], item)
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))
    covered = sum(gains)
    missing = max(0, len(set(item.paginas_esperadas)) - covered)
    ideal_gains = sorted([gain for gain in gains if gain] + [1] * missing, reverse=True)[:10]
    if not ideal_gains:
        return 0.0
    ideal = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(ideal_gains, start=1))
    return dcg / ideal if ideal else 0.0


def evaluate_retrieval(
    *,
    items: list[GoldenItem],
    index: InMemoryCosineIndex,
    embedder: Embedder,
) -> RetrievalSummary:
    """Evaluate answerable/ambiguous items and record unanswerable top scores."""
    recall_totals = {str(k): 0.0 for k in KS}
    precision_totals = {str(k): 0.0 for k in KS}
    mrr_total = 0.0
    ndcg_total = 0.0
    evaluated = 0
    unanswerable = 0
    query_latencies_ms: list[float] = []
    top_scores: list[UnanswerableTopScores] = []

    for item in items:
        query_started = time.perf_counter()
        query_vector = embedder.embed_queries([item.pergunta])[0]
        results = index.search(query_vector, top_k=10)
        query_latencies_ms.append((time.perf_counter() - query_started) * 1000)

        if item.tipo == ItemType.UNANSWERABLE:
            unanswerable += 1
            top_scores.append(
                UnanswerableTopScores(
                    item_id=item.id,
                    top_scores=[result.score for result in results],
                )
            )
            continue

        if item.tipo not in (ItemType.ANSWERABLE, ItemType.AMBIGUOUS_PARTIAL):
            continue

        evaluated += 1
        expected_pages = set(item.paginas_esperadas)
        flags = _page_relevance_flags(results, item)

        for k in KS:
            top = results[:k]
            top_flags = flags[: len(top)]
            relevant_pages = {
                page
                for result, flag in zip(top, top_flags, strict=True)
                if flag
                for page in set(result.chunk.page_numbers) & expected_pages
            }
            recall = len(relevant_pages) / len(expected_pages) if expected_pages else 0.0
            denominator = len(top)
            precision = (sum(top_flags) / denominator) if denominator else 0.0
            recall_totals[str(k)] += recall
            precision_totals[str(k)] += precision

        first_relevant_rank = next(
            (idx for idx, flag in enumerate(flags[:10], start=1) if flag),
            None,
        )
        if first_relevant_rank is not None:
            mrr_total += 1.0 / first_relevant_rank
        ndcg_total += _ndcg_at_10(results, item)

    top1_values = [scores.top_scores[0] for scores in top_scores if scores.top_scores]
    divisor = evaluated or 1
    return RetrievalSummary(
        evaluated_item_count=evaluated,
        unanswerable_item_count=unanswerable,
        recall_at={k: recall_totals[k] / divisor for k in recall_totals},
        precision_at={k: precision_totals[k] / divisor for k in precision_totals},
        mrr_at_10=mrr_total / divisor,
        ndcg_at_10=ndcg_total / divisor,
        query_latency_ms=latency_summary(query_latencies_ms),
        unanswerable_top_scores=top_scores,
        unanswerable_top_score_summary=latency_summary(top1_values),
    )
