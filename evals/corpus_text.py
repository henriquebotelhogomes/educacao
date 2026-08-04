"""
corpus_text.py — PDF text extraction and normalization for the eval corpus.

Provides deterministic, dependency-light helpers used by both the evidence
audit (:mod:`evals.evidence_audit`) and the offline authoring tooling.  Text is
extracted with ``pypdfium2`` (already available transitively via Docling), so no
network access and no extra dependency is required.

The public surface is intentionally small:

* :func:`extract_page_text` — raw text of a single 1-indexed page.
* :func:`clean_text` — collapse a raw extraction into a single readable line
  (accents/case preserved) suitable for quoting verbatim in the dataset.
* :func:`normalize_for_match` — case-folded, whitespace-collapsed form used to
  test whether an evidence quote is present on a page.
* :func:`quote_present` — normalized substring test.
* :func:`iter_sentences` — split cleaned page text into candidate sentences.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

# Characters that PDF extraction sometimes injects and that carry no semantic
# meaning: BOM variants and the Unicode soft hyphen.
_JUNK_CHARS = "".join(("\ufeff", "\ufffe", "\u00ad", "\u200b"))
_JUNK_RE = re.compile(f"[{_JUNK_CHARS}]")
_WS_RE = re.compile(r"\s+")
# Hyphen immediately followed by a line break: join the split word.
_HYPHEN_BREAK_RE = re.compile(r"-\s*\r?\n")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def clean_text(raw: str) -> str:
    """Collapse a raw PDF extraction into a single, human-readable line.

    Case and accents are preserved so the result can be quoted verbatim in the
    golden dataset.  Line-break hyphenation is repaired and all whitespace runs
    become a single space.
    """
    text = unicodedata.normalize("NFC", raw)
    text = _HYPHEN_BREAK_RE.sub("", text)
    text = _JUNK_RE.sub("", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def normalize_for_match(text: str) -> str:
    """Return the case-folded, whitespace-collapsed form used for matching."""
    return clean_text(text).casefold()


def quote_present(quote: str, page_text: str) -> bool:
    """True when ``quote`` appears in ``page_text`` under match normalization."""
    needle = normalize_for_match(quote)
    if not needle:
        return False
    return needle in normalize_for_match(page_text)


@lru_cache(maxsize=64)
def _open_document(pdf_path: str):
    import pypdfium2 as pdfium

    return pdfium.PdfDocument(pdf_path)


def extract_page_text(pdf_path: str | Path, page_number: int) -> str:
    """Extract the raw text of ``page_number`` (1-indexed) from ``pdf_path``."""
    if page_number < 1:
        raise ValueError(f"page_number must be >= 1, got {page_number}")
    document = _open_document(str(Path(pdf_path)))
    if page_number > len(document):
        raise ValueError(
            f"page {page_number} out of range for {pdf_path} (has {len(document)} pages)"
        )
    page = document[page_number - 1]
    textpage = page.get_textpage()
    try:
        return textpage.get_text_range()
    finally:
        textpage.close()
        page.close()


def extract_clean_page_text(pdf_path: str | Path, page_number: int) -> str:
    """Convenience wrapper: :func:`extract_page_text` piped through :func:`clean_text`."""
    return clean_text(extract_page_text(pdf_path, page_number))


def iter_sentences(text: str, *, min_len: int = 40, max_len: int = 240) -> list[str]:
    """Split cleaned ``text`` into candidate sentences within a length window."""
    cleaned = clean_text(text)
    sentences: list[str] = []
    for chunk in _SENTENCE_SPLIT_RE.split(cleaned):
        chunk = chunk.strip()
        if min_len <= len(chunk) <= max_len:
            sentences.append(chunk)
    return sentences
