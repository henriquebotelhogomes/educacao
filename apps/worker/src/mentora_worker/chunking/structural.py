"""Structural chunking: 512 tokens / 64 overlap, preserving page metadata (ADR-012)."""

from __future__ import annotations

import hashlib
import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, cast

from mentora_worker.extraction.docling_adapter import ExtractedDocument

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A single chunk of text with provenance metadata."""

    text: str
    page_number: int
    position: int
    content_hash: str
    token_count: int
    page_numbers: tuple[int, ...] = ()


class StructuralChunker:
    """Splits an ExtractedDocument into overlapping token-bounded chunks.

    Parameters
    ----------
    chunk_size:
        Maximum number of tokens per chunk.
    overlap:
        Number of tokens to repeat at the start of each successive chunk.
    encode_fn:
        Callable ``str → list[int]`` used to count tokens.  Defaults to a
        lazy-loaded HuggingFace tokenizer for ``intfloat/multilingual-e5-small``.
        Pass a word-split lambda in tests to avoid network/model loading.
    token_count_prefix:
        Prefix reserved inside the token budget but not stored in chunk text.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 64,
        encode_fn: Callable[[str], list[int]] | None = None,
        token_count_prefix: str = "",
    ) -> None:
        self._chunk_size = chunk_size
        self._overlap = overlap
        self._tokenizer = None  # lazy-loaded HF tokenizer
        self._encode_fn: Callable[[str], list[int]] = encode_fn or self._default_encode
        self._token_count_prefix = token_count_prefix

    def _token_count(self, text: str) -> int:
        return len(self._encode_fn(f"{self._token_count_prefix}{text}"))

    def _default_encode(self, text: str) -> list[int]:
        """Lazy-load the E5 tokenizer and encode *text* to token IDs."""
        if self._tokenizer is None:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small")
        tokenizer = cast(Any, self._tokenizer)
        return list(tokenizer.encode(text, verbose=False))

    def _split_oversized_segment(self, text: str, page_number: int) -> list[tuple[str, int]]:
        """Split one structural segment into token-bounded overlapping word windows."""
        if self._token_count(text) <= self._chunk_size:
            return [(text, page_number)]

        words = text.split()
        pieces: list[tuple[str, int]] = []
        start = 0
        while start < len(words):
            low = start + 1
            high = len(words)
            end = start
            while low <= high:
                middle = (low + high) // 2
                candidate = " ".join(words[start:middle])
                if self._token_count(candidate) <= self._chunk_size:
                    end = middle
                    low = middle + 1
                else:
                    high = middle - 1

            if end == start:
                raise ValueError(
                    "A single token cannot fit within the configured chunk_size; "
                    "increase chunk_size or use a compatible tokenizer."
                )

            pieces.append((" ".join(words[start:end]), page_number))
            if end == len(words):
                break
            start = end

        return pieces

    def chunk(self, document: ExtractedDocument) -> list[TextChunk]:
        """Segment *document* into overlapping TextChunks.

        Algorithm
        ---------
        1. Flatten the document into ``(paragraph_text, page_number)`` segments
           by splitting each page on ``\\n\\n``, then further on ``\\n``.
        2. Greedily accumulate segments into a buffer until adding the next
           segment would exceed ``chunk_size``.
        3. Emit a chunk; seed the next buffer with the trailing ``overlap``
           tokens worth of segments from the current buffer.
        4. Repeat until all segments are consumed.
        """
        segments: list[tuple[str, int]] = []
        for page in document.pages:
            for para in page.text.split("\n\n"):
                for line in para.split("\n"):
                    stripped = line.strip()
                    if stripped:
                        segments.extend(self._split_oversized_segment(stripped, page.page_number))

        if not segments:
            return []

        chunks: list[TextChunk] = []

        # Mutable accumulation buffers
        buf_texts: list[str] = []
        buf_pages: list[int] = []
        buf_token_counts: list[int] = []

        def _joined_token_count(texts: list[str]) -> int:
            return self._token_count(" ".join(texts))

        def _emit() -> None:
            if not buf_texts:
                return
            text = " ".join(buf_texts)
            page_counter: Counter[int] = Counter()
            for pg, tc in zip(buf_pages, buf_token_counts, strict=True):
                page_counter[pg] += tc
            dominant_page = page_counter.most_common(1)[0][0]
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            chunks.append(
                TextChunk(
                    text=text,
                    page_number=dominant_page,
                    position=len(chunks),
                    content_hash=content_hash,
                    token_count=_joined_token_count(buf_texts),
                    page_numbers=tuple(sorted(page_counter)),
                )
            )

        def _seed_overlap() -> tuple[list[str], list[int], list[int]]:
            """Return the largest trailing text suffix within the overlap budget."""
            if self._overlap == 0:
                return [], [], []
            new_texts: list[str] = []
            new_pages: list[int] = []
            new_counts: list[int] = []
            for bt, bp in zip(
                reversed(buf_texts),
                reversed(buf_pages),
                strict=True,
            ):
                candidate = [bt, *new_texts]
                if _joined_token_count(candidate) <= self._overlap:
                    new_texts.insert(0, bt)
                    new_pages.insert(0, bp)
                    new_counts.insert(0, self._token_count(bt))
                    continue

                words = bt.split()
                low = 0
                high = len(words) - 1
                suffix_start = len(words)
                while low <= high:
                    middle = (low + high) // 2
                    suffix = " ".join(words[middle:])
                    if _joined_token_count([suffix, *new_texts]) <= self._overlap:
                        suffix_start = middle
                        high = middle - 1
                    else:
                        low = middle + 1
                if suffix_start < len(words):
                    suffix = " ".join(words[suffix_start:])
                    new_texts.insert(0, suffix)
                    new_pages.insert(0, bp)
                    new_counts.insert(0, self._token_count(suffix))
                break
            return new_texts, new_pages, new_counts

        def _trim_overlap_to_fit(text: str) -> None:
            while buf_texts and _joined_token_count([*buf_texts, text]) > self._chunk_size:
                words = buf_texts[0].split()
                if len(words) == 1:
                    buf_texts.pop(0)
                    buf_pages.pop(0)
                    buf_token_counts.pop(0)
                    continue
                trimmed = " ".join(words[1:])
                buf_texts[0] = trimmed
                buf_token_counts[0] = self._token_count(trimmed)

        for text, page_number in segments:
            tc = self._token_count(text)
            if _joined_token_count([*buf_texts, text]) > self._chunk_size and buf_texts:
                _emit()
                buf_texts, buf_pages, buf_token_counts = _seed_overlap()
                _trim_overlap_to_fit(text)

            buf_texts.append(text)
            buf_pages.append(page_number)
            buf_token_counts.append(tc)

        _emit()
        return chunks
