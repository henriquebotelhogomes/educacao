"""Unit tests for ADR-018 corpus extraction and cache behavior."""

from __future__ import annotations

import json
import pathlib

from evals.benchmark.corpus import (
    BenchmarkPage,
    CachedCorpusExtractor,
    PypdfiumRapidOcrPageExtractor,
)


class RecordingExtractor:
    def __init__(self) -> None:
        self.calls: list[tuple[pathlib.Path, int, bool]] = []

    def extract_page(
        self,
        pdf_path: pathlib.Path,
        page_number: int,
        *,
        use_ocr_on_empty: bool,
    ) -> str:
        self.calls.append((pdf_path, page_number, use_ocr_on_empty))
        return f"text::{pdf_path.name}::{page_number}"


def _manifest(root: pathlib.Path) -> pathlib.Path:
    (root / "corpus").mkdir()
    (root / "fixtures").mkdir()
    (root / "corpus" / "normal.pdf").write_bytes(b"%PDF-normal")
    (root / "corpus" / "poor-source.pdf").write_bytes(b"%PDF-source")
    (root / "fixtures" / "poor-fixture.pdf").write_bytes(b"%PDF-fixture")
    path = root / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "filename": "normal.pdf",
                        "doc_type": "narrative",
                        "page_count": 2,
                        "corpus_path": "corpus/normal.pdf",
                        "sha256": "n",
                    },
                    {
                        "filename": "poor-fixture.pdf",
                        "doc_type": "poor_scan",
                        "page_count": 2,
                        "corpus_path": "corpus/poor-source.pdf",
                        "fixture_path": "fixtures/poor-fixture.pdf",
                        "page_map": {"1": 10, "2": 11},
                        "sha256": "p",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def test_corpus_extractor_uses_fixture_for_poor_scan_and_preserves_logical_pages(
    tmp_path: pathlib.Path,
) -> None:
    manifest_path = _manifest(tmp_path)
    extractor = RecordingExtractor()
    corpus = CachedCorpusExtractor(
        repo_root=tmp_path,
        cache_dir=tmp_path / ".cache",
        extractor=extractor,
    ).load_manifest(manifest_path, max_pages_per_document=1)

    assert corpus.pages == [
        BenchmarkPage(
            document="normal.pdf",
            page_number=1,
            text="text::normal.pdf::1",
            source_path="corpus/normal.pdf",
            source_page_number=1,
        ),
        BenchmarkPage(
            document="poor-fixture.pdf",
            page_number=1,
            text="text::poor-fixture.pdf::1",
            source_path="fixtures/poor-fixture.pdf",
            source_page_number=1,
        ),
    ]
    assert extractor.calls == [
        (tmp_path / "corpus" / "normal.pdf", 1, False),
        (tmp_path / "fixtures" / "poor-fixture.pdf", 1, True),
    ]


def test_corpus_extractor_reads_cached_pages_without_reextracting(tmp_path: pathlib.Path) -> None:
    manifest_path = _manifest(tmp_path)
    extractor = RecordingExtractor()
    cached = CachedCorpusExtractor(
        repo_root=tmp_path,
        cache_dir=tmp_path / ".cache",
        extractor=extractor,
    )

    first = cached.load_manifest(manifest_path, max_pages_per_document=1)
    second = cached.load_manifest(manifest_path, max_pages_per_document=1)

    assert first.corpus_sha256 == second.corpus_sha256
    assert len(extractor.calls) == 2


def test_rapidocr_fallback_reuses_engine_across_pages(tmp_path: pathlib.Path, monkeypatch) -> None:
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-scan")
    monkeypatch.setattr("evals.benchmark.corpus.extract_page_text", lambda *_: "")

    factory_calls = 0
    ocr_calls: list[str] = []

    class Result:
        def __init__(self, text: str) -> None:
            self.txts = (text,)

    class Engine:
        def __call__(self, image: str) -> Result:
            ocr_calls.append(image)
            return Result(f"texto {image}")

    def ocr_factory() -> Engine:
        nonlocal factory_calls
        factory_calls += 1
        return Engine()

    extractor = PypdfiumRapidOcrPageExtractor(
        ocr_factory=ocr_factory,
        page_renderer=lambda _, page: f"imagem-{page}",
    )

    assert extractor.extract_page(pdf_path, 1, use_ocr_on_empty=True) == "texto imagem-1"
    assert extractor.extract_page(pdf_path, 2, use_ocr_on_empty=True) == "texto imagem-2"
    assert factory_calls == 1
    assert ocr_calls == ["imagem-1", "imagem-2"]
