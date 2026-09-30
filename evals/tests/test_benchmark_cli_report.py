"""Unit tests for ADR-018 benchmark CLI validation, fake smoke, and reports."""

from __future__ import annotations

import json
import pathlib

import pytest

from evals.benchmark import cli
from evals.benchmark.chunking_experiment import ChunkingVariant
from evals.benchmark.hashing import canonical_sha256, sha256_file
from evals.benchmark.publishability import effective_document_hashes
from evals.benchmark.registry import CANDIDATES
from evals.benchmark.report import render_markdown_comparison
from evals.benchmark.runner import fake_smoke_result, make_config


def test_cli_rejects_unknown_model_alias(tmp_path: pathlib.Path) -> None:
    output = tmp_path / "result.json"

    exit_code = cli.main(
        [
            "run",
            "--model",
            "does-not-exist",
            "--dataset",
            str(tmp_path / "missing.jsonl"),
            "--manifest",
            str(tmp_path / "missing-manifest.json"),
            "--output",
            str(output),
            "--offline",
        ]
    )

    assert exit_code != 0


def test_fake_smoke_command_writes_provisional_result_without_pdf_or_model_work(
    tmp_path: pathlib.Path,
) -> None:
    output = tmp_path / "smoke.json"

    exit_code = cli.main(["smoke", "--output", str(output)])

    assert exit_code == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["model"]["alias"] == "fake-smoke"
    assert result["publishability"]["publishable"] is False
    assert "PROVISIONAL" in result["publishability"]["label"]
    assert result["metrics"]["evaluated_item_count"] == 1


def test_report_renderer_labels_draft_results_as_provisional() -> None:
    markdown = render_markdown_comparison(
        [
            {
                "model": {"alias": "e5-small"},
                "dataset": {"status": "draft", "review_counts": {"draft": 120}},
                "publishability": {"publishable": False, "label": "PROVISIONAL"},
                "metrics": {
                    "recall_at": {"1": 0.25, "3": 0.5, "5": 0.75, "10": 1.0},
                    "precision_at": {"1": 0.25, "3": 0.2, "5": 0.15, "10": 0.1},
                    "mrr_at_10": 0.5,
                    "ndcg_at_10": 0.6,
                    "query_latency_ms": {"p50": 12.0, "p95": 20.0},
                },
                "timings": {"corpus_encoding_ms": 100.0, "index_build_ms": 3.0},
                "corpus": {"chunk_count": 10, "page_count": 2},
            }
        ]
    )

    assert "PROVISIONAL" in markdown
    assert "e5-small" in markdown
    assert "Recall@10" in markdown


def test_embedding_report_rejects_mismatched_dataset_hashes() -> None:
    def result(dataset_hash: str) -> dict[str, object]:
        return {
            "schema_version": "adr-018-benchmark-result-v1",
            "adr": "ADR-018",
            "experiment_type": "embedding",
            "model": {"alias": "e5-small"},
            "config": {
                "chunk_size": 512,
                "chunk_overlap": 64,
                "chunk_tokenizer_name": "intfloat/multilingual-e5-small",
                "max_items": None,
                "max_pages_per_document": None,
                "device": "cpu",
            },
            "hashes": {
                "dataset_sha256": dataset_hash,
                "manifest_sha256": "manifest",
                "corpus_sha256": "corpus",
                "document_hashes_sha256": "documents",
            },
            "publishability": {"publishable": False},
            "metrics": {},
            "timings": {},
            "corpus": {},
        }

    with pytest.raises(ValueError, match="dataset_sha256"):
        render_markdown_comparison([result("one"), result("two")])


def test_chunking_command_runs_the_six_adr_012_variants(
    tmp_path: pathlib.Path,
    monkeypatch,
) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "results"
    dataset.write_text("", encoding="utf-8")
    manifest.write_text('{"documents": []}', encoding="utf-8")
    observed_versions: list[str] = []

    def fake_run_benchmark(**kwargs):
        variant = kwargs["chunking_variant"]
        observed_versions.append(variant.strategy_version)
        return fake_smoke_result()

    monkeypatch.setattr(cli, "run_benchmark", fake_run_benchmark)

    exit_code = cli.main(
        [
            "chunking",
            "--model",
            "e5-small",
            "--dataset",
            str(dataset),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
            "--offline",
        ]
    )

    assert exit_code == 0
    assert observed_versions == [
        "structural-v1-t256-o32",
        "structural-v1-t512-o64",
        "structural-v1-t1024-o128",
        "semantic-percentile-v1-t256-o32",
        "semantic-percentile-v1-t512-o64",
        "semantic-percentile-v1-t1024-o128",
    ]
    assert sorted(path.name for path in output.glob("*.json")) == sorted(
        f"{version}.json" for version in observed_versions
    )


def test_chunking_command_can_resume_one_filtered_variant(
    tmp_path: pathlib.Path,
    monkeypatch,
) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    dataset.write_text("", encoding="utf-8")
    manifest.write_text('{"documents": []}', encoding="utf-8")
    observed_versions: list[str] = []

    def fake_run_benchmark(**kwargs):
        observed_versions.append(kwargs["chunking_variant"].strategy_version)
        return fake_smoke_result()

    monkeypatch.setattr(cli, "run_benchmark", fake_run_benchmark)

    exit_code = cli.main(
        [
            "chunking",
            "--model",
            "e5-small",
            "--dataset",
            str(dataset),
            "--manifest",
            str(manifest),
            "--output",
            str(tmp_path / "results"),
            "--strategy",
            "semantic",
            "--chunk-size",
            "512",
        ]
    )

    assert exit_code == 0
    assert observed_versions == ["semantic-percentile-v1-t512-o64"]


def test_existing_chunking_result_matches_config_and_input_hashes(
    tmp_path: pathlib.Path,
) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    document = tmp_path / "doc.pdf"
    dataset.write_text('{"id":"one"}\n', encoding="utf-8")
    document.write_bytes(b"%PDF-original")
    manifest.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "filename": "doc.pdf",
                        "corpus_path": str(document),
                        "sha256": sha256_file(document),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    config = make_config(
        candidate=CANDIDATES["e5-small"],
        dataset_path=dataset,
        manifest_path=manifest,
        output_path=tmp_path / "result.json",
        device="cpu",
        offline=True,
        max_pages_per_document=None,
        max_items=None,
        publish_requested=False,
        chunking_variant=ChunkingVariant("semantic", 512, 64),
    )
    result = {
        "model": {"model_name": config.model_name},
        "hashes": {
            "config_sha256": canonical_sha256(config.deterministic_payload()),
            "dataset_sha256": sha256_file(dataset),
            "manifest_sha256": sha256_file(manifest),
            "document_hashes_sha256": canonical_sha256(
                effective_document_hashes(
                    json.loads(manifest.read_text(encoding="utf-8")),
                    repo_root=tmp_path,
                )
            ),
        },
    }

    assert cli.existing_result_matches_config(
        result,
        config=config,
        dataset_path=dataset,
        manifest_path=manifest,
    )

    document.write_bytes(b"%PDF-stale")
    assert not cli.existing_result_matches_config(
        result,
        config=config,
        dataset_path=dataset,
        manifest_path=manifest,
    )
