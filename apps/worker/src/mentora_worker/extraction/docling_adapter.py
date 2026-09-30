"""Docling extraction adapter — text + page metadata."""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PageBlock:
    """Text extracted from a single page."""

    page_number: int
    text: str


@dataclass
class ExtractedDocument:
    """Document text grouped by page."""

    pages: list[PageBlock]
    title: str | None = field(default=None)


class DoclingExtractor:
    """Converts document bytes to structured text via Docling (lazy-loaded).

    The DocumentConverter is instantiated once per class (class-level singleton)
    to avoid paying the model-loading cost on every extraction.
    """

    _converter: Any | None = None

    @classmethod
    def _get_converter(cls) -> Any:
        if cls._converter is None:
            from docling.document_converter import DocumentConverter

            cls._converter = DocumentConverter()
        return cls._converter

    def extract(self, data: bytes, filename: str = "document.pdf") -> ExtractedDocument:
        """Convert *data* bytes to an ExtractedDocument with per-page text blocks."""
        suffix = os.path.splitext(filename)[1] or ".pdf"
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
                fh.write(data)
                tmp_path = fh.name

            converter = self._get_converter()
            result = converter.convert(tmp_path)

            pages: dict[int, str] = {}
            for item, _level in result.document.iterate_items():
                text = getattr(item, "text", None)
                if not text:
                    continue
                page_no = 1
                prov = getattr(item, "prov", None)
                if prov:
                    page_no = getattr(prov[0], "page_no", 1)
                existing = pages.get(page_no, "")
                pages[page_no] = f"{existing}\n{text}".strip() if existing else text

            return ExtractedDocument(
                pages=[PageBlock(page_number=k, text=v) for k, v in sorted(pages.items())]
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
