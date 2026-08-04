"""
evidence_audit.py — Verify that every evidence quote really appears on its page.

For each ``answerable`` / ``ambiguous_partial`` golden item the audit:

1. Resolves the document's ``corpus_path`` from the manifest (never assumes
   ``support/ebooks``: a poor-scan fixture's ``corpus_path`` points at the
   original text source).
2. Translates each ``paginas_esperadas`` entry through the document's
   ``page_map`` (identity when absent) to the source page number.
3. Extracts and normalizes the text of those pages.
4. Asserts each ``evidence_quotes`` snippet is present under normalization.

``unanswerable`` items are required to carry no pages/evidence and are skipped.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

from evals.corpus_text import extract_page_text, quote_present


@dataclass
class EvidenceFailure:
    item_id: str
    documento: str
    reason: str


@dataclass
class EvidenceReport:
    checked_items: int = 0
    checked_quotes: int = 0
    failures: list[EvidenceFailure] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def _source_page(page_map: dict[str, int] | None, page: int) -> int:
    if page_map is None:
        return page
    return page_map.get(str(page), page)


def audit_evidence(
    items: list[dict],
    manifest: dict,
    repo_root: pathlib.Path,
) -> EvidenceReport:
    """Audit evidence quotes for all answerable/ambiguous items.

    Returns an :class:`EvidenceReport`; ``report.ok`` is False when any quote is
    missing from its expected page(s) or a referenced document/page is invalid.
    """
    docs = {d["filename"]: d for d in manifest.get("documents", [])}
    report = EvidenceReport()

    for item in items:
        tipo = item.get("tipo")
        if tipo not in ("answerable", "ambiguous_partial"):
            continue

        item_id = item.get("id", "?")
        documento = item.get("documento", "")
        quotes = item.get("evidence_quotes") or []
        pages = item.get("paginas_esperadas") or []
        report.checked_items += 1

        doc = docs.get(documento)
        if doc is None:
            report.failures.append(
                EvidenceFailure(item_id, documento, "document not present in manifest")
            )
            continue

        corpus_path = repo_root / doc["corpus_path"]
        if not corpus_path.exists():
            report.failures.append(
                EvidenceFailure(item_id, documento, f"corpus_path not found: {corpus_path}")
            )
            continue

        page_map = doc.get("page_map")
        page_texts: list[str] = []
        page_error = False
        for page in pages:
            source_page = _source_page(page_map, page)
            try:
                page_texts.append(extract_page_text(corpus_path, source_page))
            except ValueError as exc:
                report.failures.append(EvidenceFailure(item_id, documento, f"page {page}: {exc}"))
                page_error = True
        if page_error:
            continue

        combined = "\n".join(page_texts)
        for quote in quotes:
            report.checked_quotes += 1
            if not quote_present(quote, combined):
                preview = quote if len(quote) <= 80 else quote[:77] + "..."
                report.failures.append(
                    EvidenceFailure(
                        item_id,
                        documento,
                        f"evidence quote not found on pages {pages}: {preview!r}",
                    )
                )

    return report
