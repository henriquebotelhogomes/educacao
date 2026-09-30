"""Unit tests for ADR-018 deterministic hashes and publishability gate."""

from __future__ import annotations

import json
import pathlib

from evals.benchmark.hashing import canonical_sha256, sha256_file
from evals.benchmark.publishability import assess_publishability
from evals.schema import Difficulty, GoldenItem, ItemType, ReviewStatus


def _approved_item() -> dict[str, object]:
    return GoldenItem(
        id="v1-test-001",
        pergunta="Pergunta?",
        resposta_referencia="Resposta.",
        documento="doc-a.pdf",
        paginas_esperadas=[1],
        evidence_quotes=["Resposta."],
        tipo=ItemType.ANSWERABLE,
        dificuldade=Difficulty.FACIL,
        review_status=ReviewStatus.APPROVED,
        notas=None,
    ).model_dump(mode="json")


def _write_jsonl(path: pathlib.Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_canonical_sha256_is_independent_of_dict_key_order() -> None:
    left = {"b": [2, 1], "a": {"z": "fim", "m": "meio"}}
    right = {"a": {"m": "meio", "z": "fim"}, "b": [2, 1]}

    assert canonical_sha256(left) == canonical_sha256(right)


def test_file_hash_changes_when_dataset_bytes_change(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text('{"id":"a"}\n', encoding="utf-8")
    first = sha256_file(path)

    path.write_text('{"id":"b"}\n', encoding="utf-8")

    assert sha256_file(path) != first


def test_draft_manifest_is_never_publishable_and_explains_blocker(tmp_path: pathlib.Path) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    _write_jsonl(dataset, [_approved_item()])
    manifest.write_text(json.dumps({"status": "draft", "version": "v1"}), encoding="utf-8")

    status = assess_publishability(dataset_path=dataset, manifest_path=manifest)

    assert not status.publishable
    assert any("draft" in reason.lower() for reason in status.blocker_reasons)
    assert "PROVISIONAL" in status.label


def test_frozen_approved_dataset_with_matching_lock_is_publishable(tmp_path: pathlib.Path) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    lock = tmp_path / "lock.json"
    item = _approved_item()
    document = tmp_path / "doc-a.pdf"
    document.write_bytes(b"%PDF-frozen")
    document_hash = sha256_file(document)
    _write_jsonl(dataset, [item])
    manifest.write_text(
        json.dumps(
            {
                "status": "frozen",
                "version": "v1",
                "item_count": 1,
                "composition": {"answerable": 1, "unanswerable": 0, "ambiguous_partial": 0},
                "documents": [
                    {
                        "filename": "doc-a.pdf",
                        "corpus_path": str(document),
                        "sha256": document_hash,
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    lock.write_text(
        json.dumps(
            {
                "dataset_sha256": sha256_file(dataset),
                "manifest_sha256": sha256_file(manifest),
                "item_count": 1,
                "composition": {"answerable": 1, "unanswerable": 0, "ambiguous_partial": 0},
                "document_hashes": {"doc-a.pdf": document_hash},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    status = assess_publishability(
        dataset_path=dataset,
        manifest_path=manifest,
        lock_path=lock,
    )

    assert status.publishable
    assert status.blocker_reasons == []


def test_limited_run_is_never_publishable(tmp_path: pathlib.Path) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    _write_jsonl(dataset, [_approved_item()])
    manifest.write_text(json.dumps({"status": "frozen", "version": "v1"}), encoding="utf-8")

    status = assess_publishability(
        dataset_path=dataset,
        manifest_path=manifest,
        max_items=1,
    )

    assert not status.publishable
    assert any("limited" in reason.lower() for reason in status.blocker_reasons)


def test_modified_corpus_file_breaks_publishability(tmp_path: pathlib.Path) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    lock = tmp_path / "lock.json"
    document = tmp_path / "doc-a.pdf"
    document.write_bytes(b"%PDF-original")
    _write_jsonl(dataset, [_approved_item()])
    document_hash = sha256_file(document)
    manifest.write_text(
        json.dumps(
            {
                "status": "frozen",
                "version": "v1",
                "item_count": 1,
                "composition": {"answerable": 1, "unanswerable": 0, "ambiguous_partial": 0},
                "documents": [
                    {
                        "filename": "doc-a.pdf",
                        "corpus_path": str(document),
                        "sha256": document_hash,
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    lock.write_text(
        json.dumps(
            {
                "dataset_sha256": sha256_file(dataset),
                "manifest_sha256": sha256_file(manifest),
                "item_count": 1,
                "composition": {"answerable": 1, "unanswerable": 0, "ambiguous_partial": 0},
                "document_hashes": {"doc-a.pdf": document_hash},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    document.write_bytes(b"%PDF-modified")

    status = assess_publishability(
        dataset_path=dataset,
        manifest_path=manifest,
        lock_path=lock,
    )

    assert not status.publishable
    assert any("doc-a.pdf" in reason for reason in status.blocker_reasons)
