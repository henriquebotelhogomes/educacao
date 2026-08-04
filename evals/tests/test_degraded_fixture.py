"""Tests for the degraded-fixture generator (evals/generate_degraded_fixture.py).

The fixture must be an *image-only* multipage PDF: text extraction from it is
empty/negligible, while the raster pages still visibly carry the source content
(so evidence remains auditable against the original text source via page_map).
"""

from __future__ import annotations

import hashlib
import json
import pathlib

from evals.corpus_text import extract_page_text
from evals.tests.conftest import (
    EVALS_ROOT,
    FIXTURE_PATH,
    POOR_SCAN_SOURCE_PATH,
)

SOURCE_PDF = POOR_SCAN_SOURCE_PATH
GENERATE_SCRIPT = EVALS_ROOT / "generate_degraded_fixture.py"
# A small, fast subset of representative pages for tmp-path regeneration tests.
SAMPLE_PAGES = [18, 20, 22]


class TestDegradedFixtureGenerator:
    def test_source_pdf_exists(self) -> None:
        assert SOURCE_PDF.exists(), f"Source PDF not found: {SOURCE_PDF}"

    def test_generate_script_exists(self) -> None:
        assert GENERATE_SCRIPT.exists(), f"Generator script not found: {GENERATE_SCRIPT}"

    def test_generates_pdf_fixture(self, tmp_path: pathlib.Path) -> None:
        from evals.generate_degraded_fixture import generate_degraded_fixture

        output = generate_degraded_fixture(
            source_pdf=SOURCE_PDF,
            output_dir=tmp_path,
            pages=SAMPLE_PAGES,
            seed=42,
        )
        assert output.exists()
        assert output.suffix == ".pdf"
        assert output.stat().st_size > 0

    def test_output_filename_hints_at_source(self, tmp_path: pathlib.Path) -> None:
        from evals.generate_degraded_fixture import generate_degraded_fixture

        output = generate_degraded_fixture(
            source_pdf=SOURCE_PDF,
            output_dir=tmp_path,
            pages=SAMPLE_PAGES,
            seed=42,
        )
        name = output.name.lower()
        assert "cerrado" in name or "scan" in name

    def test_generation_is_reproducible(self, tmp_path: pathlib.Path) -> None:
        """Same source + pages + seed + dpi → identical output bytes."""
        from evals.generate_degraded_fixture import generate_degraded_fixture

        out1 = generate_degraded_fixture(SOURCE_PDF, tmp_path / "run1", pages=SAMPLE_PAGES, seed=42)
        out2 = generate_degraded_fixture(SOURCE_PDF, tmp_path / "run2", pages=SAMPLE_PAGES, seed=42)
        h1 = hashlib.sha256(out1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(out2.read_bytes()).hexdigest()
        assert h1 == h2, "Fixture generation must be reproducible with same inputs"

    def test_fixture_is_image_only_no_text(self, tmp_path: pathlib.Path) -> None:
        """Text extraction from the generated fixture must be empty/negligible."""
        from evals.generate_degraded_fixture import generate_degraded_fixture

        output = generate_degraded_fixture(SOURCE_PDF, tmp_path, pages=SAMPLE_PAGES, seed=42)
        for page in range(1, len(SAMPLE_PAGES) + 1):
            text = extract_page_text(output, page).strip()
            assert text == "", f"Fixture page {page} unexpectedly carries text: {text!r}"

    def test_source_pages_actually_carry_text(self) -> None:
        """Sanity: the *source* pages selected do carry extractable text."""
        for page in SAMPLE_PAGES:
            text = extract_page_text(SOURCE_PDF, page).strip()
            assert len(text) > 50, f"Source page {page} has too little text to ground items"

    def test_page_count_matches_selection(self, tmp_path: pathlib.Path) -> None:
        import pypdfium2 as pdfium

        from evals.generate_degraded_fixture import generate_degraded_fixture

        output = generate_degraded_fixture(SOURCE_PDF, tmp_path, pages=SAMPLE_PAGES, seed=42)
        doc = pdfium.PdfDocument(str(output))
        try:
            assert len(doc) == len(SAMPLE_PAGES)
        finally:
            doc.close()

    def test_provenance_json_written_with_page_map(self, tmp_path: pathlib.Path) -> None:
        from evals.generate_degraded_fixture import generate_degraded_fixture

        generate_degraded_fixture(SOURCE_PDF, tmp_path, pages=SAMPLE_PAGES, seed=42)
        provenance_files = list(tmp_path.glob("*provenance*.json"))
        assert provenance_files, "A provenance JSON must be written alongside the fixture"
        prov = json.loads(provenance_files[0].read_text(encoding="utf-8"))
        assert "source_pdf" in prov
        assert "source_sha256" in prov
        assert "fixture_sha256" in prov
        assert prov["fixture_page_count"] == len(SAMPLE_PAGES)
        # page_map keys are 1-indexed fixture pages, values are source pages.
        assert prov["page_map"] == {"1": 18, "2": 20, "3": 22}


class TestCommittedFixture:
    """Checks against the committed, canonical fixture used by the dataset."""

    def test_committed_fixture_exists(self) -> None:
        assert FIXTURE_PATH.exists(), f"Committed fixture not found: {FIXTURE_PATH}"

    def test_committed_fixture_is_image_only(self) -> None:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(FIXTURE_PATH))
        try:
            page_count = len(doc)
        finally:
            doc.close()
        assert page_count == 18
        for page in range(1, page_count + 1):
            assert (
                extract_page_text(FIXTURE_PATH, page).strip() == ""
            ), f"Committed fixture page {page} must carry no extractable text"
