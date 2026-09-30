"""Tests for deliberate application of human review decisions."""

from __future__ import annotations

import csv
import json
import pathlib

import pytest

from evals.apply_review import apply_review_csv


def _write_dataset(path: pathlib.Path) -> None:
    rows = [
        {
            "id": "answerable",
            "tipo": "answerable",
            "review_status": "draft",
        },
        {
            "id": "unanswerable",
            "tipo": "unanswerable",
            "review_status": "draft",
        },
        {
            "id": "change-requested",
            "tipo": "answerable",
            "review_status": "draft",
        },
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_decisions(path: pathlib.Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["id", "decisao_do_revisor", "comentario_do_revisor"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"id": "answerable", "decisao_do_revisor": "reviewed_ok"},
                {"id": "unanswerable", "decisao_do_revisor": "draft"},
                {
                    "id": "change-requested",
                    "decisao_do_revisor": "reviewed_changes_requested",
                },
            ]
        )


def test_apply_review_approves_only_explicit_and_authorized_unanswerable_drafts(
    tmp_path: pathlib.Path,
) -> None:
    dataset = tmp_path / "golden.jsonl"
    decisions = tmp_path / "review-decisions.csv"
    _write_dataset(dataset)
    _write_decisions(decisions)

    summary = apply_review_csv(
        dataset_path=dataset,
        decisions_path=decisions,
        approve_unanswerable_ids={"unanswerable"},
    )

    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    assert [row["review_status"] for row in rows] == ["approved", "approved", "draft"]
    assert summary.approved_from_review == 1
    assert summary.approved_unanswerable_drafts == 1
    assert summary.unresolved_ids == ("change-requested",)


def test_apply_review_rejects_unexpected_decision_ids(tmp_path: pathlib.Path) -> None:
    dataset = tmp_path / "golden.jsonl"
    decisions = tmp_path / "review-decisions.csv"
    _write_dataset(dataset)
    _write_decisions(decisions)
    with decisions.open("a", encoding="utf-8", newline="") as file:
        csv.writer(file).writerow(["not-in-dataset", "reviewed_ok", ""])

    with pytest.raises(ValueError, match="not present"):
        apply_review_csv(dataset_path=dataset, decisions_path=decisions)


def test_apply_review_keeps_prior_authorized_approval_when_csv_still_says_draft(
    tmp_path: pathlib.Path,
) -> None:
    dataset = tmp_path / "golden.jsonl"
    decisions = tmp_path / "review-decisions.csv"
    _write_dataset(dataset)
    _write_decisions(decisions)
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    rows[1]["review_status"] = "approved"
    dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    summary = apply_review_csv(dataset_path=dataset, decisions_path=decisions)

    assert summary.unresolved_ids == ("change-requested",)
    updated = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    assert updated[1]["review_status"] == "approved"
