"""Tests for the degraded-fixture generator (evals/generate_degraded_fixture.py)."""

from __future__ import annotations

import hashlib
import pathlib

from evals.tests.conftest import EVALS_ROOT, SUPPORT_EBOOKS

SOURCE_PDF = SUPPORT_EBOOKS / "ph,+Gerente+da+editora,+cerrado-goiano.pdf"
GENERATE_SCRIPT = EVALS_ROOT / "generate_degraded_fixture.py"


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
            n_pages=5,
            seed=42,
        )
        assert output.exists()
        assert output.suffix == ".pdf"
        assert output.stat().st_size > 0

    def test_output_filename_contains_provenance(self, tmp_path: pathlib.Path) -> None:
        from evals.generate_degraded_fixture import generate_degraded_fixture

        output = generate_degraded_fixture(
            source_pdf=SOURCE_PDF,
            output_dir=tmp_path,
            n_pages=5,
            seed=42,
        )
        # Fixture filename must hint at source
        name = output.name.lower()
        assert "cerrado" in name or "fixture" in name or "scan" in name

    def test_generation_is_reproducible(self, tmp_path: pathlib.Path) -> None:
        """Same seed + same input → same output bytes (no randomness in page extraction)."""
        from evals.generate_degraded_fixture import generate_degraded_fixture

        out1 = generate_degraded_fixture(SOURCE_PDF, tmp_path / "run1", n_pages=3, seed=42)
        out2 = generate_degraded_fixture(SOURCE_PDF, tmp_path / "run2", n_pages=3, seed=42)
        (tmp_path / "run1").mkdir(parents=True, exist_ok=True)
        (tmp_path / "run2").mkdir(parents=True, exist_ok=True)
        h1 = hashlib.sha256(out1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(out2.read_bytes()).hexdigest()
        assert h1 == h2, "Fixture generation must be reproducible with same seed"

    def test_generates_scan_noise_images(self, tmp_path: pathlib.Path) -> None:
        from evals.generate_degraded_fixture import generate_scan_noise_images

        images = generate_scan_noise_images(output_dir=tmp_path, n_pages=3, seed=42)
        assert len(images) == 3
        for img_path in images:
            assert img_path.exists()
            assert img_path.suffix == ".png"
            assert img_path.stat().st_size > 0

    def test_scan_images_reproducible(self, tmp_path: pathlib.Path) -> None:
        from evals.generate_degraded_fixture import generate_scan_noise_images

        imgs1 = generate_scan_noise_images(tmp_path / "r1", n_pages=2, seed=99)
        imgs2 = generate_scan_noise_images(tmp_path / "r2", n_pages=2, seed=99)
        (tmp_path / "r1").mkdir(parents=True, exist_ok=True)
        (tmp_path / "r2").mkdir(parents=True, exist_ok=True)
        for i1, i2 in zip(imgs1, imgs2, strict=True):
            h1 = hashlib.sha256(i1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(i2.read_bytes()).hexdigest()
            assert h1 == h2, f"Image {i1.name} not reproducible"

    def test_different_seeds_produce_different_images(self, tmp_path: pathlib.Path) -> None:
        from evals.generate_degraded_fixture import generate_scan_noise_images

        imgs_a = generate_scan_noise_images(tmp_path / "a", n_pages=1, seed=1)
        imgs_b = generate_scan_noise_images(tmp_path / "b", n_pages=1, seed=2)
        (tmp_path / "a").mkdir(parents=True, exist_ok=True)
        (tmp_path / "b").mkdir(parents=True, exist_ok=True)
        h_a = hashlib.sha256(imgs_a[0].read_bytes()).hexdigest()
        h_b = hashlib.sha256(imgs_b[0].read_bytes()).hexdigest()
        assert h_a != h_b, "Different seeds must produce different images"

    def test_provenance_json_written(self, tmp_path: pathlib.Path) -> None:
        import json

        from evals.generate_degraded_fixture import generate_degraded_fixture

        generate_degraded_fixture(SOURCE_PDF, tmp_path, n_pages=3, seed=42)
        provenance_files = list(tmp_path.glob("*provenance*.json"))
        assert provenance_files, "A provenance JSON must be written alongside the fixture"
        prov = json.loads(provenance_files[0].read_text(encoding="utf-8"))
        assert "source_pdf" in prov
        assert "source_sha256" in prov
        assert "n_pages" in prov
        assert "seed" in prov
