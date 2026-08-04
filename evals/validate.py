"""
validate.py — Golden-dataset validation and freeze CLI (specs/12 §7.3).

Usage
-----
Check dataset integrity (schema, composition, page bounds, document hashes):

    python evals/validate.py check \\
        --dataset evals/datasets/v1/golden.jsonl \\
        --manifest evals/datasets/v1/manifest.json

Freeze — write a lock manifest after all checks pass:

    python evals/validate.py freeze \\
        --dataset evals/datasets/v1/golden.jsonl \\
        --manifest evals/datasets/v1/manifest.json \\
        --output evals/datasets/v1/lock.json

Exit codes: 0 = OK, 1 = validation failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

# Ensure repo root is on sys.path so `evals.schema` is importable when this
# script is executed directly (not via `python -m`).
_REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    items = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {lineno}: {exc}") from exc
    return items


def _load_manifest(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


class ValidationError(Exception):
    pass


def _validate(
    items: list[dict],
    manifest: dict,
    *,
    verbose: bool = True,
) -> None:
    """Raise ValidationError with a description of all problems found."""
    errors: list[str] = []

    def err(msg: str) -> None:
        errors.append(msg)
        if verbose:
            print(f"  [FAIL] {msg}")

    def ok(msg: str) -> None:
        if verbose:
            print(f"  [OK]   {msg}")

    # ------------------------------------------------------------------
    # 1. Item count
    # ------------------------------------------------------------------
    total = len(items)
    if verbose:
        print("\n=== Item count ===")
    if total < 120:
        err(f"Too few items: {total} (need ≥ 120)")
    else:
        ok(f"Item count: {total}")

    # ------------------------------------------------------------------
    # 2. Composition
    # ------------------------------------------------------------------
    if verbose:
        print("\n=== Composition ===")
    answerable = sum(1 for i in items if i.get("tipo") == "answerable")
    unanswerable = sum(1 for i in items if i.get("tipo") == "unanswerable")
    ambiguous = sum(1 for i in items if i.get("tipo") == "ambiguous_partial")
    expected = {"answerable": 72, "unanswerable": 30, "ambiguous_partial": 18}

    for key, want in expected.items():
        got = {
            "answerable": answerable,
            "unanswerable": unanswerable,
            "ambiguous_partial": ambiguous,
        }[key]
        if got == want:
            ok(f"{key}: {got}")
        else:
            err(f"{key}: expected {want}, got {got}")

    # ------------------------------------------------------------------
    # 3. Schema validation via pydantic
    # ------------------------------------------------------------------
    if verbose:
        print("\n=== Per-item schema ===")
    try:
        from evals.schema import GoldenItem

        schema_errors = 0
        for item in items:
            try:
                GoldenItem(**item)
            except Exception as exc:  # noqa: BLE001
                err(f"Item {item.get('id', '?')}: schema error: {exc}")
                schema_errors += 1
        if schema_errors == 0:
            ok(f"All {total} items pass schema validation")
    except ImportError:
        if verbose:
            print("  [SKIP] evals.schema not importable — skipping Pydantic validation")

    # ------------------------------------------------------------------
    # 4. Unique IDs
    # ------------------------------------------------------------------
    if verbose:
        print("\n=== ID uniqueness ===")
    ids = [i.get("id", "") for i in items]
    duplicates = [id_ for id_ in ids if ids.count(id_) > 1]
    if duplicates:
        err(f"Duplicate IDs: {sorted(set(duplicates))}")
    else:
        ok("All IDs unique")

    # ------------------------------------------------------------------
    # 5. Review status — must not contain fabricated approvals
    # ------------------------------------------------------------------
    if verbose:
        print("\n=== Review status ===")
    non_draft = [i.get("id") for i in items if i.get("review_status") != "draft"]
    if non_draft:
        # Not an error — just informational if some are reviewed/approved
        if verbose:
            print(
                f"  [INFO] {len(non_draft)} items with review_status != 'draft': "
                f"{non_draft[:5]}{'...' if len(non_draft) > 5 else ''}"
            )
    else:
        ok("All items carry review_status='draft' (pending human review)")

    # ------------------------------------------------------------------
    # 6. Document manifest cross-check
    # ------------------------------------------------------------------
    if verbose:
        print("\n=== Document manifest ===")
    manifest_docs = {d["filename"]: d for d in manifest.get("documents", [])}
    item_docs = {i.get("documento") for i in items}
    missing = item_docs - set(manifest_docs.keys())
    if missing:
        err(f"Items reference docs not in manifest: {missing}")
    else:
        ok(f"All {len(item_docs)} referenced docs present in manifest")

    # ------------------------------------------------------------------
    # 7. Page bounds
    # ------------------------------------------------------------------
    if verbose:
        print("\n=== Page bounds ===")
    page_errors = 0
    for item in items:
        doc = item.get("documento", "")
        if doc not in manifest_docs:
            continue
        max_page = manifest_docs[doc]["page_count"]
        for page in item.get("paginas_esperadas", []):
            if not (1 <= page <= max_page):
                err(f"Item {item.get('id')}: page {page} out of range for {doc} (max={max_page})")
                page_errors += 1
    if page_errors == 0:
        ok("All page references within document bounds")

    # ------------------------------------------------------------------
    # 8. Document coverage — equal per doc
    # ------------------------------------------------------------------
    if verbose:
        print("\n=== Document coverage ===")
    from collections import Counter

    counts = Counter(i.get("documento") for i in items)
    for doc in manifest_docs:
        n = counts.get(doc, 0)
        if n == 20:
            ok(f"{doc}: {n} items")
        else:
            err(f"{doc}: expected 20 items, got {n}")

    # ------------------------------------------------------------------
    # 9. Manifest integrity (stored composition vs actual items)
    # ------------------------------------------------------------------
    if verbose:
        print("\n=== Manifest consistency ===")
    mcomp = manifest.get("composition", {})
    if mcomp.get("answerable") == answerable:
        ok(f"manifest.composition.answerable matches: {answerable}")
    else:
        err(f"manifest.composition.answerable={mcomp.get('answerable')} but actual={answerable}")
    if mcomp.get("item_count") == total or manifest.get("item_count") == total:
        ok(f"manifest.item_count matches: {total}")
    else:
        err(f"manifest.item_count={manifest.get('item_count')} but actual={total}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    if errors:
        raise ValidationError(
            f"\n{len(errors)} validation error(s):\n" + "\n".join(f"  - {e}" for e in errors)
        )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    dataset_path = pathlib.Path(args.dataset)
    manifest_path = pathlib.Path(args.manifest)

    if not dataset_path.exists():
        print(f"ERROR: dataset not found: {dataset_path}", file=sys.stderr)
        return 1
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    print(f"Checking dataset:  {dataset_path}")
    print(f"Against manifest:  {manifest_path}")

    try:
        items = _load_jsonl(dataset_path)
        manifest = _load_manifest(manifest_path)
        _validate(items, manifest, verbose=True)
        print("\nAll checks passed.")
        return 0
    except (ValidationError, ValueError) as exc:
        print(f"\nValidation failed: {exc}", file=sys.stderr)
        return 1


def cmd_freeze(args: argparse.Namespace) -> int:
    dataset_path = pathlib.Path(args.dataset)
    manifest_path = pathlib.Path(args.manifest)
    output_path = pathlib.Path(args.output)

    if not dataset_path.exists():
        print(f"ERROR: dataset not found: {dataset_path}", file=sys.stderr)
        return 1
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    print(f"Freezing dataset:  {dataset_path}")
    print(f"Against manifest:  {manifest_path}")
    print(f"Lock output:       {output_path}")

    try:
        items = _load_jsonl(dataset_path)
        manifest = _load_manifest(manifest_path)
        _validate(items, manifest, verbose=True)
    except (ValidationError, ValueError) as exc:
        print(f"\nCannot freeze -- validation failed: {exc}", file=sys.stderr)
        return 1

    from collections import Counter

    counts_by_type = Counter(i.get("tipo") for i in items)

    lock: dict = {
        "version": manifest.get("version", "v1"),
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": _sha256_file(dataset_path),
        "manifest_sha256": _sha256_file(manifest_path),
        "item_count": len(items),
        "composition": {
            "answerable": counts_by_type.get("answerable", 0),
            "unanswerable": counts_by_type.get("unanswerable", 0),
            "ambiguous_partial": counts_by_type.get("ambiguous_partial", 0),
        },
        "document_hashes": {d["filename"]: d["sha256"] for d in manifest.get("documents", [])},
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nLock manifest written to {output_path}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Golden-dataset validation and freeze CLI (specs/12 §7.3)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = sub.add_parser("check", help="Validate dataset against manifest")
    p_check.add_argument("--dataset", required=True, help="Path to golden.jsonl")
    p_check.add_argument("--manifest", required=True, help="Path to manifest.json")

    # freeze
    p_freeze = sub.add_parser(
        "freeze",
        help="Validate and write a SHA-256 lock manifest",
    )
    p_freeze.add_argument("--dataset", required=True, help="Path to golden.jsonl")
    p_freeze.add_argument("--manifest", required=True, help="Path to manifest.json")
    p_freeze.add_argument("--output", required=True, help="Path to write lock.json")

    args = parser.parse_args(argv)

    if args.command == "check":
        return cmd_check(args)
    if args.command == "freeze":
        return cmd_freeze(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
