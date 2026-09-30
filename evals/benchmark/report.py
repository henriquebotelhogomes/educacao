"""Markdown report rendering for ADR-018 benchmark result JSON files."""

from __future__ import annotations

import json
import pathlib
from typing import Any

from evals.benchmark.registry import CANDIDATES


def _fmt(value: Any) -> str:
    if isinstance(value, (float, int)):
        return f"{float(value):.4g}"
    return str(value)


def render_markdown_comparison(results: list[dict[str, Any]]) -> str:
    """Render a deterministic Markdown comparison table."""
    _validate_embedding_controls(results)
    sorted_results = sorted(results, key=lambda result: result.get("model", {}).get("alias", ""))
    any_provisional = any(
        not bool(result.get("publishability", {}).get("publishable", False))
        for result in sorted_results
    )
    title = "# ADR-018 Embedding Benchmark Comparison"
    if any_provisional:
        title += " — PROVISIONAL"
    lines = [
        title,
        "",
        "| Model | Input validity | Status | Recall@1 | Recall@3 | Recall@5 | Recall@10 | "
        "Precision@10 | MRR@10 | NDCG@10 | p50 query ms | p95 query ms | "
        "Corpus encode ms | Chunks | Pages |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in sorted_results:
        metrics = result.get("metrics", {})
        recall = metrics.get("recall_at", {})
        precision = metrics.get("precision_at", {})
        latency = metrics.get("query_latency_ms", {})
        timings = result.get("timings", {})
        corpus = result.get("corpus", {})
        publishability = result.get("publishability", {})
        status = publishability.get("label") or (
            "PUBLISHABLE" if publishability.get("publishable") else "PROVISIONAL"
        )
        lines.append(
            "| {model} | {validity} | {status} | {r1} | {r3} | {r5} | {r10} | {p10} | {mrr} | "
            "{ndcg} | {p50} | {p95} | {encode} | {chunks} | {pages} |".format(
                model=result.get("model", {}).get("alias", "?"),
                validity=(
                    "VALID"
                    if result.get("embedding_inputs", {}).get("valid")
                    else "INVALID_TRUNCATION"
                ),
                status=status,
                r1=_fmt(recall.get("1", 0.0)),
                r3=_fmt(recall.get("3", 0.0)),
                r5=_fmt(recall.get("5", 0.0)),
                r10=_fmt(recall.get("10", 0.0)),
                p10=_fmt(precision.get("10", 0.0)),
                mrr=_fmt(metrics.get("mrr_at_10", 0.0)),
                ndcg=_fmt(metrics.get("ndcg_at_10", 0.0)),
                p50=_fmt(latency.get("p50", 0.0)),
                p95=_fmt(latency.get("p95", 0.0)),
                encode=_fmt(timings.get("corpus_encoding_ms", 0.0)),
                chunks=corpus.get("chunk_count", 0),
                pages=corpus.get("page_count", 0),
            )
        )
    if any_provisional:
        lines.extend(
            [
                "",
                "**PROVISIONAL:** at least one result is based on a draft or otherwise "
                "non-publishable dataset. Do not cite these numbers as ADR ratification.",
            ]
        )
    return "\n".join(lines) + "\n"


def render_chunking_markdown_comparison(results: list[dict[str, Any]]) -> str:
    """Render a deterministic ADR-012 strategy comparison table."""
    _validate_chunking_controls(results)
    sorted_results = sorted(
        results,
        key=lambda result: result.get("config", {}).get("chunking_strategy_version", ""),
    )
    any_provisional = any(
        not bool(result.get("publishability", {}).get("publishable", False))
        for result in sorted_results
    )
    title = "# ADR-012 Chunking Benchmark Comparison"
    if any_provisional:
        title += " — PROVISIONAL"
    lines = [
        title,
        "",
        "| Strategy | Version | Model | Validity | Status | Recall@10 | MRR@10 | NDCG@10 | "
        "p95 query ms | Chunking ms | Corpus encode ms | Chunks |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in sorted_results:
        config = result.get("config", {})
        metrics = result.get("metrics", {})
        timings = result.get("timings", {})
        publishability = result.get("publishability", {})
        lines.append(
            "| {strategy} | {version} | {model} | {validity} | {status} | {recall} | {mrr} | "
            "{ndcg} | {p95} | {chunking} | {encoding} | {chunks} |".format(
                strategy=config.get("chunking_strategy", "?"),
                version=config.get("chunking_strategy_version", "?"),
                model=result.get("model", {}).get("alias", "?"),
                validity=chunking_result_validity(result),
                status=publishability.get("label", "PROVISIONAL"),
                recall=_fmt(metrics.get("recall_at", {}).get("10", 0.0)),
                mrr=_fmt(metrics.get("mrr_at_10", 0.0)),
                ndcg=_fmt(metrics.get("ndcg_at_10", 0.0)),
                p95=_fmt(metrics.get("query_latency_ms", {}).get("p95", 0.0)),
                chunking=_fmt(timings.get("chunking_ms", 0.0)),
                encoding=_fmt(timings.get("corpus_encoding_ms", 0.0)),
                chunks=result.get("corpus", {}).get("chunk_count", 0),
            )
        )
    if any_provisional:
        lines.extend(
            [
                "",
                "**PROVISIONAL:** the dataset is not frozen and approved. "
                "Do not use this comparison to ratify ADR-012.",
            ]
        )
    return "\n".join(lines) + "\n"


def chunking_result_validity(result: dict[str, Any]) -> str:
    alias = result.get("model", {}).get("alias")
    candidate = CANDIDATES.get(str(alias))
    if candidate is None:
        return "UNKNOWN_MODEL"
    chunk_size = result.get("config", {}).get("chunk_size")
    if not isinstance(chunk_size, int):
        return "MISSING_CHUNK_SIZE"
    if chunk_size > candidate.max_sequence_tokens:
        return "INVALID_MODEL_LIMIT"
    return "VALID"


def _validate_chunking_controls(results: list[dict[str, Any]]) -> None:
    if len(results) < 2:
        return
    _validate_result_identity(
        results,
        schema_version="adr-012-benchmark-result-v1",
        adr="ADR-012",
        experiment_type="chunking",
    )
    controls = {
        "model_name": ("model", "model_name"),
        "dataset_sha256": ("hashes", "dataset_sha256"),
        "manifest_sha256": ("hashes", "manifest_sha256"),
        "corpus_sha256": ("hashes", "corpus_sha256"),
        "document_hashes_sha256": ("hashes", "document_hashes_sha256"),
        "chunk_tokenizer_name": ("config", "chunk_tokenizer_name"),
        "max_items": ("config", "max_items"),
        "max_pages_per_document": ("config", "max_pages_per_document"),
        "device": ("config", "device"),
    }
    _validate_equal_controls(results, controls, experiment="chunking")


def _validate_embedding_controls(results: list[dict[str, Any]]) -> None:
    if len(results) < 2:
        return
    _validate_result_identity(
        results,
        schema_version="adr-018-benchmark-result-v1",
        adr="ADR-018",
        experiment_type="embedding",
    )
    controls = {
        "dataset_sha256": ("hashes", "dataset_sha256"),
        "manifest_sha256": ("hashes", "manifest_sha256"),
        "corpus_sha256": ("hashes", "corpus_sha256"),
        "document_hashes_sha256": ("hashes", "document_hashes_sha256"),
        "chunk_size": ("config", "chunk_size"),
        "chunk_overlap": ("config", "chunk_overlap"),
        "chunk_tokenizer_name": ("config", "chunk_tokenizer_name"),
        "max_items": ("config", "max_items"),
        "max_pages_per_document": ("config", "max_pages_per_document"),
        "device": ("config", "device"),
    }
    _validate_equal_controls(results, controls, experiment="embedding")


def _validate_result_identity(
    results: list[dict[str, Any]],
    *,
    schema_version: str,
    adr: str,
    experiment_type: str,
) -> None:
    expected = {
        "schema_version": schema_version,
        "adr": adr,
        "experiment_type": experiment_type,
    }
    for result in results:
        for field, value in expected.items():
            if result.get(field) != value:
                raise ValueError(
                    f"{experiment_type} comparison has invalid {field}: {result.get(field)!r}"
                )


def _validate_equal_controls(
    results: list[dict[str, Any]],
    controls: dict[str, tuple[str, str]],
    *,
    experiment: str,
) -> None:
    for name, (section, field) in controls.items():
        values: list[Any] = []
        for result in results:
            container = result.get(section)
            if not isinstance(container, dict) or field not in container:
                raise ValueError(f"{experiment} comparison is missing controlled field: {name}")
            values.append(container[field])
        if len(set(values)) != 1:
            raise ValueError(f"{experiment} comparison has mismatched controlled field: {name}")


def load_result_jsons(paths: list[pathlib.Path]) -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]
