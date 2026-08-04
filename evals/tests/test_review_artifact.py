"""Tests for the offline review-artifact generator (evals/review_artifact.py)."""

from __future__ import annotations

import pathlib

from evals.review_artifact import build_rows, generate, render_csv, render_html
from evals.tests.conftest import (
    GOLDEN_PATH,
    MANIFEST_PATH,
    POOR_SCAN_FILENAME,
    TOTAL_ITEMS,
)


def _load_rows() -> list[dict]:
    import json

    items = [
        json.loads(line)
        for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return build_rows(items, manifest)


class TestReviewArtifactRows:
    def test_one_row_per_item(self) -> None:
        rows = _load_rows()
        assert len(rows) == TOTAL_ITEMS

    def test_all_rows_carry_current_draft_status(self) -> None:
        for row in _load_rows():
            assert row["review_status"] == "draft"

    def test_poor_scan_rows_resolve_source_pages(self) -> None:
        rows = [r for r in _load_rows() if r["documento"] == POOR_SCAN_FILENAME]
        grounded = [r for r in rows if r["paginas_fixture"]]
        assert grounded
        for row in grounded:
            # fixture pages differ from source pages via page_map (e.g. 2 -> 20)
            assert row["paginas_fonte"] != [] and row["paginas_fixture"] != []
            assert max(row["paginas_fonte"]) >= max(row["paginas_fixture"])


class TestReviewArtifactRendering:
    def test_csv_has_header_and_all_rows(self) -> None:
        csv_text = render_csv(_load_rows())
        lines = [ln for ln in csv_text.splitlines() if ln]
        assert lines[0].startswith("id,tipo,dificuldade")
        assert len(lines) == TOTAL_ITEMS + 1

    def test_csv_exposes_evidence_and_source(self) -> None:
        csv_text = render_csv(_load_rows())
        assert "corpus_path" in csv_text
        assert "evidence_quotes" in csv_text
        assert "decisao_do_revisor" in csv_text

    def test_html_is_standalone_and_has_content(self) -> None:
        html_text = render_html(_load_rows())
        assert html_text.strip().startswith("<!DOCTYPE html>")
        # no external resources / server required
        assert "http://" not in html_text and "https://" not in html_text
        assert "Decisão do revisor" in html_text

    def test_html_does_not_mark_items_reviewed(self) -> None:
        """The artifact must never pre-mark items as reviewed."""
        html_text = render_html(_load_rows())
        # Every item's current status shown is draft.
        assert "status atual: " in html_text
        # The review states are available to the reviewer (built client-side)...
        assert "reviewed_ok" in html_text
        # ...but no embedded item data carries a reviewed/approved status.
        assert '"review_status": "reviewed"' not in html_text
        assert '"review_status": "approved"' not in html_text
        assert '"review_status":"reviewed"' not in html_text
        # The default per-item decision is 'draft'.
        assert 'decision: "draft"' in html_text


class TestReviewArtifactGenerate:
    def test_generate_both_formats(self, tmp_path: pathlib.Path) -> None:
        written = generate(GOLDEN_PATH, MANIFEST_PATH, tmp_path / "review", "both")
        names = {p.name for p in written}
        assert names == {"review.html", "review.csv"}
        for path in written:
            assert path.exists() and path.stat().st_size > 0

    def test_generation_is_deterministic(self, tmp_path: pathlib.Path) -> None:
        generate(GOLDEN_PATH, MANIFEST_PATH, tmp_path / "a", "both")
        generate(GOLDEN_PATH, MANIFEST_PATH, tmp_path / "b", "both")
        assert (tmp_path / "a.html").read_bytes() == (tmp_path / "b.html").read_bytes()
        assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()

    def test_does_not_mutate_dataset(self, tmp_path: pathlib.Path) -> None:
        before = GOLDEN_PATH.read_bytes()
        generate(GOLDEN_PATH, MANIFEST_PATH, tmp_path / "review", "both")
        assert GOLDEN_PATH.read_bytes() == before
