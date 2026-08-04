"""Tests for the evidence audit (evals/evidence_audit.py).

The audit is the semantic backbone of the corpus: it extracts the *expected*
PDF pages (through the manifest ``corpus_path`` and, for the poor-scan fixture,
the ``page_map``) and asserts each ``evidence_quotes`` snippet is really present.
"""

from __future__ import annotations

import copy

from evals.evidence_audit import audit_evidence
from evals.tests.conftest import POOR_SCAN_FILENAME, REPO_ROOT


class TestEvidenceAuditOnRealDataset:
    def test_all_quotes_present(self, golden_items: list[dict], manifest_data: dict) -> None:
        report = audit_evidence(golden_items, manifest_data, REPO_ROOT)
        assert report.ok, "\n".join(f"{f.item_id}: {f.reason}" for f in report.failures)
        assert report.checked_items == 90  # 72 answerable + 18 ambiguous
        assert report.checked_quotes >= 90

    def test_unanswerable_items_are_skipped(
        self, golden_items: list[dict], manifest_data: dict
    ) -> None:
        only_unanswerable = [i for i in golden_items if i["tipo"] == "unanswerable"]
        report = audit_evidence(only_unanswerable, manifest_data, REPO_ROOT)
        assert report.checked_items == 0
        assert report.checked_quotes == 0
        assert report.ok


class TestEvidenceAuditDetectsCorruption:
    def test_corrupted_quote_fails(self, golden_items: list[dict], manifest_data: dict) -> None:
        """A quote that is NOT on the expected page must fail the audit."""
        items = copy.deepcopy(golden_items)
        target = next(i for i in items if i["tipo"] == "answerable")
        target["evidence_quotes"] = ["esta frase inventada nao aparece em nenhuma pagina do corpus"]
        report = audit_evidence(items, manifest_data, REPO_ROOT)
        assert not report.ok
        assert any(f.item_id == target["id"] for f in report.failures)

    def test_quote_on_wrong_page_fails(self, golden_items: list[dict], manifest_data: dict) -> None:
        """A real quote pointed at the wrong page must fail."""
        items = copy.deepcopy(golden_items)
        # Pick a text-doc item whose evidence sits deep in the book, then
        # re-point it at page 2 (front matter), which cannot contain it.
        target = next(
            i
            for i in items
            if i["tipo"] == "answerable"
            and i["documento"] == "História Agrária.pdf"
            and min(i["paginas_esperadas"]) > 10
        )
        target["paginas_esperadas"] = [2]
        report = audit_evidence(items, manifest_data, REPO_ROOT)
        assert not report.ok
        assert any(f.item_id == target["id"] for f in report.failures)


class TestEvidenceAuditPageMap:
    def test_poor_scan_uses_page_map(self, golden_items: list[dict], manifest_data: dict) -> None:
        """Poor-scan items reference fixture pages; the audit resolves via page_map."""
        cg_items = [i for i in golden_items if i["documento"] == POOR_SCAN_FILENAME]
        answerable_cg = [i for i in cg_items if i["tipo"] in ("answerable", "ambiguous_partial")]
        assert answerable_cg, "expected grounded poor-scan items"
        # All referenced pages are fixture pages within 1..18.
        for item in answerable_cg:
            for page in item["paginas_esperadas"]:
                assert 1 <= page <= 18
        report = audit_evidence(answerable_cg, manifest_data, REPO_ROOT)
        assert report.ok, "\n".join(f"{f.item_id}: {f.reason}" for f in report.failures)

    def test_missing_corpus_path_is_reported(
        self, golden_items: list[dict], manifest_data: dict
    ) -> None:
        manifest = copy.deepcopy(manifest_data)
        for doc in manifest["documents"]:
            doc["corpus_path"] = "support/ebooks/does-not-exist.pdf"
        answerable = [i for i in golden_items if i["tipo"] == "answerable"][:1]
        report = audit_evidence(answerable, manifest, REPO_ROOT)
        assert not report.ok
        assert "corpus_path not found" in report.failures[0].reason
