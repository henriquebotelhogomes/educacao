"""Corpus extraction and cache abstraction for ADR-018 benchmarks."""

from __future__ import annotations

import json
import pathlib
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from evals.benchmark.hashing import canonical_sha256, sha256_file
from evals.corpus_text import clean_text, extract_page_text


@dataclass(frozen=True)
class BenchmarkPage:
    document: str
    page_number: int
    text: str
    source_path: str
    source_page_number: int


@dataclass(frozen=True)
class ExtractedCorpus:
    pages: list[BenchmarkPage]
    corpus_sha256: str
    extraction_ms: float


class PageExtractor(Protocol):
    def extract_page(
        self,
        pdf_path: pathlib.Path,
        page_number: int,
        *,
        use_ocr_on_empty: bool,
    ) -> str: ...


class PypdfiumRapidOcrPageExtractor:
    """Local pypdfium2 extraction with a lightweight RapidOCR fallback."""

    extractor_version = "pypdfium2-rapidocr-v1"

    def __init__(
        self,
        ocr_factory: Callable[[], Any] | None = None,
        page_renderer: Callable[[pathlib.Path, int], Any] | None = None,
    ) -> None:
        self._ocr_factory = ocr_factory
        self._page_renderer = page_renderer or self._render_page
        self._ocr_engine: Any | None = None

    def extract_page(
        self,
        pdf_path: pathlib.Path,
        page_number: int,
        *,
        use_ocr_on_empty: bool,
    ) -> str:
        text = clean_text(extract_page_text(pdf_path, page_number))
        if text or not use_ocr_on_empty:
            return text
        return self._extract_ocr_page(pdf_path, page_number)

    def _extract_ocr_page(self, pdf_path: pathlib.Path, page_number: int) -> str:
        if self._ocr_engine is None:
            if self._ocr_factory is not None:
                self._ocr_engine = self._ocr_factory()
            else:
                from rapidocr import RapidOCR

                self._ocr_engine = RapidOCR()
        result = self._ocr_engine(self._page_renderer(pdf_path, page_number))
        texts = getattr(result, "txts", None)
        return clean_text("\n".join(str(text) for text in texts or ()))

    @staticmethod
    def _render_page(pdf_path: pathlib.Path, page_number: int) -> Any:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(str(pdf_path))
        try:
            page = document[page_number - 1]
            try:
                bitmap = page.render(scale=2.0)
                try:
                    return bitmap.to_pil().copy()
                finally:
                    bitmap.close()
            finally:
                page.close()
        finally:
            document.close()


class CachedCorpusExtractor:
    """Extract logical manifest pages and persist page text in an ignored cache."""

    def __init__(
        self,
        *,
        repo_root: pathlib.Path,
        cache_dir: pathlib.Path,
        extractor: PageExtractor | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.cache_dir = cache_dir
        self.extractor = extractor or PypdfiumRapidOcrPageExtractor()

    def load_manifest(
        self,
        manifest_path: pathlib.Path,
        *,
        max_pages_per_document: int | None = None,
    ) -> ExtractedCorpus:
        started = time.perf_counter()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_hash = sha256_file(manifest_path)
        pages: list[BenchmarkPage] = []
        for document in manifest.get("documents", []):
            page_count = int(document["page_count"])
            if max_pages_per_document is not None:
                page_count = min(page_count, max_pages_per_document)
            source_path = self._document_benchmark_path(document)
            use_ocr = document.get("doc_type") == "poor_scan"
            for logical_page in range(1, page_count + 1):
                pages.append(
                    self._load_or_extract_page(
                        manifest_hash=manifest_hash,
                        document_name=str(document["filename"]),
                        pdf_path=source_path,
                        logical_page=logical_page,
                        use_ocr_on_empty=use_ocr,
                    )
                )
        corpus_hash = canonical_sha256(
            [
                {
                    "document": page.document,
                    "page_number": page.page_number,
                    "source_path": page.source_path,
                    "source_page_number": page.source_page_number,
                    "text_sha256": canonical_sha256(page.text),
                }
                for page in pages
            ]
        )
        return ExtractedCorpus(
            pages=pages,
            corpus_sha256=corpus_hash,
            extraction_ms=(time.perf_counter() - started) * 1000,
        )

    def _document_benchmark_path(self, document: dict[str, object]) -> pathlib.Path:
        if document.get("doc_type") == "poor_scan" and document.get("fixture_path"):
            return self.repo_root / str(document["fixture_path"])
        return self.repo_root / str(document["corpus_path"])

    def _load_or_extract_page(
        self,
        *,
        manifest_hash: str,
        document_name: str,
        pdf_path: pathlib.Path,
        logical_page: int,
        use_ocr_on_empty: bool,
    ) -> BenchmarkPage:
        source_hash = sha256_file(pdf_path)
        rel_source = self._repo_relative(pdf_path)
        cache_path = self._cache_path(
            manifest_hash=manifest_hash,
            document_name=document_name,
            source_hash=source_hash,
            page_number=logical_page,
        )
        cached = self._read_cache(
            cache_path=cache_path,
            document_name=document_name,
            source_path=rel_source,
            source_hash=source_hash,
            logical_page=logical_page,
        )
        if cached is not None:
            return cached

        text = self.extractor.extract_page(
            pdf_path,
            logical_page,
            use_ocr_on_empty=use_ocr_on_empty,
        )
        page = BenchmarkPage(
            document=document_name,
            page_number=logical_page,
            text=text,
            source_path=rel_source,
            source_page_number=logical_page,
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_payload = {
            "document": page.document,
            "page_number": page.page_number,
            "text": page.text,
            "source_path": page.source_path,
            "source_page_number": page.source_page_number,
            "source_sha256": source_hash,
            "extractor_version": self._extractor_version,
        }
        cache_path.write_text(
            json.dumps(cache_payload, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        return page

    def _read_cache(
        self,
        *,
        cache_path: pathlib.Path,
        document_name: str,
        source_path: str,
        source_hash: str,
        logical_page: int,
    ) -> BenchmarkPage | None:
        if not cache_path.exists():
            return None
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        expected = {
            "document": document_name,
            "page_number": logical_page,
            "source_path": source_path,
            "source_sha256": source_hash,
            "extractor_version": self._extractor_version,
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            return None
        return BenchmarkPage(
            document=str(payload["document"]),
            page_number=int(payload["page_number"]),
            text=str(payload.get("text", "")),
            source_path=str(payload["source_path"]),
            source_page_number=int(payload.get("source_page_number", logical_page)),
        )

    def _cache_path(
        self,
        *,
        manifest_hash: str,
        document_name: str,
        source_hash: str,
        page_number: int,
    ) -> pathlib.Path:
        safe_doc = re.sub(r"[^A-Za-z0-9_.-]+", "_", document_name).strip("_") or "document"
        return (
            self.cache_dir
            / "pages"
            / manifest_hash
            / f"{safe_doc}-{source_hash[:12]}"
            / f"{page_number:05d}.json"
        )

    @property
    def _extractor_version(self) -> str:
        return str(getattr(self.extractor, "extractor_version", "injected-v1"))

    def _repo_relative(self, path: pathlib.Path) -> str:
        try:
            return path.relative_to(self.repo_root).as_posix()
        except ValueError:
            return str(path)
