"""Publishability gate for ADR-018 benchmark artifacts."""

from __future__ import annotations

import json
import pathlib
from collections import Counter

from evals.benchmark.hashing import sha256_file
from evals.benchmark.schemas import PublishabilityStatus
from evals.schema import GoldenItem, ReviewStatus


def _load_items(dataset_path: pathlib.Path) -> list[GoldenItem]:
    items: list[GoldenItem] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            items.append(GoldenItem.model_validate(json.loads(stripped)))
    return items


def review_counts(items: list[GoldenItem]) -> dict[str, int]:
    counts = Counter(item.review_status.value for item in items)
    return {
        "draft": counts.get("draft", 0),
        "reviewed": counts.get("reviewed", 0),
        "approved": counts.get("approved", 0),
    }


def assess_publishability(
    *,
    dataset_path: pathlib.Path,
    manifest_path: pathlib.Path,
    lock_path: pathlib.Path | None = None,
    repo_root: pathlib.Path | None = None,
    max_items: int | None = None,
    max_pages_per_document: int | None = None,
) -> PublishabilityStatus:
    """Return whether a benchmark result may be treated as publishable."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = _load_items(dataset_path)
    blockers: list[str] = []
    if max_items is not None or max_pages_per_document is not None:
        blockers.append(
            "Limited benchmark runs are PROVISIONAL and cannot be published "
            f"(max_items={max_items}, max_pages_per_document={max_pages_per_document})."
        )

    status = str(manifest.get("status", ""))
    if status != "frozen":
        blockers.append(
            f"Manifest status is {status!r}; draft/non-frozen datasets are PROVISIONAL only."
        )

    counts = review_counts(items)
    if counts["approved"] != len(items):
        blockers.append(
            "Not all dataset items are approved "
            f"(approved={counts['approved']}, total={len(items)})."
        )

    type_counts = Counter(item.tipo.value for item in items)
    actual_composition = {
        "answerable": type_counts.get("answerable", 0),
        "unanswerable": type_counts.get("unanswerable", 0),
        "ambiguous_partial": type_counts.get("ambiguous_partial", 0),
    }
    if manifest.get("item_count") != len(items):
        blockers.append("Manifest item_count does not match current dataset item count.")
    if manifest.get("composition") != actual_composition:
        blockers.append("Manifest composition does not match current dataset composition.")

    document_hashes = effective_document_hashes(
        manifest,
        repo_root=repo_root or manifest_path.parent,
        blockers=blockers,
    )

    effective_lock = lock_path or (manifest_path.parent / "lock.json")
    if not effective_lock.exists():
        blockers.append(f"Lock manifest not found: {effective_lock}")
    else:
        lock = json.loads(effective_lock.read_text(encoding="utf-8"))
        dataset_hash = sha256_file(dataset_path)
        manifest_hash = sha256_file(manifest_path)
        if lock.get("dataset_sha256") != dataset_hash:
            blockers.append("Lock dataset_sha256 does not match current dataset bytes.")
        if lock.get("manifest_sha256") != manifest_hash:
            blockers.append("Lock manifest_sha256 does not match current manifest bytes.")
        if lock.get("item_count") != len(items):
            blockers.append("Lock item_count does not match current dataset item count.")
        if lock.get("composition") != actual_composition:
            blockers.append("Lock composition does not match current dataset composition.")
        if lock.get("document_hashes") != document_hashes:
            blockers.append("Lock document_hashes do not match current corpus files.")

    return PublishabilityStatus(
        publishable=not blockers,
        label="PUBLISHABLE" if not blockers else "PROVISIONAL",
        blocker_reasons=blockers,
        lock_path=str(effective_lock),
    )


def effective_document_hashes(
    manifest: dict[str, object],
    *,
    repo_root: pathlib.Path,
    blockers: list[str] | None = None,
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    effective_blockers = blockers if blockers is not None else []
    documents = manifest.get("documents")
    if not isinstance(documents, list) or not documents:
        effective_blockers.append("Manifest documents must be a non-empty list.")
        return resolved
    for raw_document in documents:
        if not isinstance(raw_document, dict):
            effective_blockers.append("Manifest contains an invalid document entry.")
            continue
        filename = raw_document.get("filename")
        expected_hash = raw_document.get("sha256")
        path_value = raw_document.get("fixture_path") or raw_document.get("corpus_path")
        if (
            not isinstance(filename, str)
            or not filename
            or not isinstance(expected_hash, str)
            or not expected_hash
            or not isinstance(path_value, str)
            or not path_value
        ):
            effective_blockers.append("Manifest document entry is missing filename/path/sha256.")
            continue
        path = pathlib.Path(path_value)
        if not path.is_absolute():
            path = repo_root / path
        if not path.exists():
            effective_blockers.append(f"Corpus document does not exist: {filename}")
            continue
        current_hash = sha256_file(path)
        resolved[filename] = current_hash
        if current_hash != expected_hash:
            effective_blockers.append(
                f"Corpus document hash does not match manifest for {filename}."
            )
    return resolved


def all_items_approved(items: list[GoldenItem]) -> bool:
    return all(item.review_status == ReviewStatus.APPROVED for item in items)
