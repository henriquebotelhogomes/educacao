"""Apply exported human review decisions to a golden dataset deliberately."""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewApplicationSummary:
    approved_from_review: int
    approved_unanswerable_drafts: int
    unresolved_ids: tuple[str, ...]


def _load_dataset(path: pathlib.Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _load_decisions(path: pathlib.Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    decisions: dict[str, str] = {}
    for row in rows:
        item_id = (row.get("id") or "").strip()
        decision = (row.get("decisao_do_revisor") or "").strip()
        if not item_id or not decision:
            raise ValueError("Every review CSV row must contain id and decisao_do_revisor.")
        if item_id in decisions:
            raise ValueError(f"Duplicate review decision for {item_id}.")
        decisions[item_id] = decision
    return decisions


def apply_review_csv(
    *,
    dataset_path: pathlib.Path,
    decisions_path: pathlib.Path,
    approve_unanswerable_ids: set[str] | None = None,
) -> ReviewApplicationSummary:
    """Apply reviewed_ok and explicitly authorized unanswerable draft decisions."""
    rows = _load_dataset(dataset_path)
    decisions = _load_decisions(decisions_path)
    row_ids = {str(row.get("id", "")) for row in rows}
    unknown_ids = sorted(set(decisions) - row_ids)
    if unknown_ids:
        raise ValueError(f"Review decision IDs not present in dataset: {unknown_ids}")
    missing_ids = sorted(row_ids - set(decisions))
    if missing_ids:
        raise ValueError(f"Dataset IDs missing from review CSV: {missing_ids}")

    authorized_drafts = approve_unanswerable_ids or set()
    approved_from_review = 0
    approved_unanswerable_drafts = 0
    unresolved: list[str] = []
    for row in rows:
        item_id = str(row["id"])
        decision = decisions[item_id]
        if decision == "reviewed_ok":
            row["review_status"] = "approved"
            approved_from_review += 1
        elif decision == "draft" and row.get("review_status") == "approved":
            continue
        elif decision == "draft" and item_id in authorized_drafts:
            if row.get("tipo") != "unanswerable":
                raise ValueError(f"Only unanswerable drafts may be explicitly approved: {item_id}")
            row["review_status"] = "approved"
            approved_unanswerable_drafts += 1
        else:
            unresolved.append(item_id)

    dataset_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return ReviewApplicationSummary(
        approved_from_review=approved_from_review,
        approved_unanswerable_drafts=approved_unanswerable_drafts,
        unresolved_ids=tuple(sorted(unresolved)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply exported golden dataset review decisions")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument(
        "--approve-unanswerable-id",
        action="append",
        default=[],
        help="Explicitly approve one CSV draft decision only when it is unanswerable",
    )
    args = parser.parse_args(argv)
    summary = apply_review_csv(
        dataset_path=pathlib.Path(args.dataset),
        decisions_path=pathlib.Path(args.decisions),
        approve_unanswerable_ids=set(args.approve_unanswerable_id),
    )
    print(
        "Applied review decisions: "
        f"approved_from_review={summary.approved_from_review}, "
        f"approved_unanswerable_drafts={summary.approved_unanswerable_drafts}, "
        f"unresolved={len(summary.unresolved_ids)}"
    )
    if summary.unresolved_ids:
        print(f"Unresolved IDs: {', '.join(summary.unresolved_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
