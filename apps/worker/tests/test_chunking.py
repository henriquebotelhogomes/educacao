"""Tests for StructuralChunker — uses a word-split encode_fn (no model loading)."""

from __future__ import annotations

import hashlib

from mentora_worker.chunking.structural import StructuralChunker, TextChunk
from mentora_worker.extraction.docling_adapter import ExtractedDocument, PageBlock

# Word-level tokeniser proxy so tests never load the real HF tokenizer.
_word_encode = lambda text: text.split()  # noqa: E731


def _make_doc(*page_texts: str) -> ExtractedDocument:
    return ExtractedDocument(
        pages=[PageBlock(page_number=i + 1, text=t) for i, t in enumerate(page_texts)]
    )


def test_single_page_produces_at_least_one_chunk() -> None:
    doc = _make_doc("hello world foo bar baz")
    chunker = StructuralChunker(chunk_size=512, overlap=64, encode_fn=_word_encode)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 1


def test_long_text_produces_multiple_chunks() -> None:
    # 5 paragraphs of 3 words each → 15 tokens total
    # chunk_size=10, overlap=3 → should yield 2 chunks
    paragraphs = "\n\n".join(
        [
            "alpha beta gamma",
            "delta epsilon zeta",
            "eta theta iota",
            "kappa lambda mu",
            "nu xi omicron",
        ]
    )
    doc = _make_doc(paragraphs)
    chunker = StructuralChunker(chunk_size=10, overlap=3, encode_fn=_word_encode)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 2


def test_single_oversized_paragraph_is_split_without_model_truncation() -> None:
    doc = _make_doc(" ".join(f"token-{index}" for index in range(25)))
    chunker = StructuralChunker(chunk_size=10, overlap=2, encode_fn=_word_encode)

    chunks = chunker.chunk(doc)

    assert len(chunks) >= 3
    assert all(chunk.token_count <= 10 for chunk in chunks)
    assert "token-0" in chunks[0].text
    assert "token-24" in chunks[-1].text


def test_consecutive_chunks_share_overlap_text() -> None:
    paragraphs = "\n\n".join(
        [
            "alpha beta gamma",
            "delta epsilon zeta",
            "eta theta iota",
            "kappa lambda mu",
            "nu xi omicron",
        ]
    )
    doc = _make_doc(paragraphs)
    chunker = StructuralChunker(chunk_size=10, overlap=3, encode_fn=_word_encode)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 2
    # The first chunk's tail text should appear in the second chunk.
    first_words = set(chunks[0].text.split())
    second_words = set(chunks[1].text.split())
    assert first_words & second_words, "Consecutive chunks should share overlapping words."


def test_overlap_keeps_token_bounded_suffix_when_segment_is_larger_than_budget() -> None:
    doc = _make_doc("one two three four five six\nseven eight nine ten eleven twelve")
    chunker = StructuralChunker(chunk_size=10, overlap=4, encode_fn=_word_encode)

    chunks = chunker.chunk(doc)

    assert chunks[0].text.split()[-4:] == chunks[1].text.split()[:4]


def test_chunk_limit_uses_token_count_of_joined_text_not_sum_of_segments() -> None:
    def non_additive_encode(text: str) -> list[int]:
        words = text.split()
        return list(range(max(0, len(words) * 2 - 1)))

    doc = _make_doc("a\nb\nc")
    chunker = StructuralChunker(chunk_size=3, overlap=0, encode_fn=non_additive_encode)

    chunks = chunker.chunk(doc)

    assert [chunk.text for chunk in chunks] == ["a b", "c"]
    assert all(len(non_additive_encode(chunk.text)) <= 3 for chunk in chunks)
    assert [chunk.token_count for chunk in chunks] == [3, 1]


def test_embedding_prefix_is_reserved_inside_chunk_limit() -> None:
    doc = _make_doc("one two three")
    chunker = StructuralChunker(
        chunk_size=3,
        overlap=0,
        encode_fn=_word_encode,
        token_count_prefix="passage: ",
    )

    chunks = chunker.chunk(doc)

    assert [chunk.text for chunk in chunks] == ["one two", "three"]
    assert [chunk.token_count for chunk in chunks] == [3, 2]


def test_content_hash_matches_sha256_of_text() -> None:
    doc = _make_doc("one two three")
    chunker = StructuralChunker(chunk_size=512, overlap=64, encode_fn=_word_encode)
    chunks = chunker.chunk(doc)
    for chunk in chunks:
        expected = hashlib.sha256(chunk.text.encode()).hexdigest()
        assert chunk.content_hash == expected


def test_position_is_zero_based_sequential() -> None:
    paragraphs = "\n\n".join(["a b c d e", "f g h i j", "k l m n o", "p q r s t"])
    doc = _make_doc(paragraphs)
    chunker = StructuralChunker(chunk_size=6, overlap=2, encode_fn=_word_encode)
    chunks = chunker.chunk(doc)
    for i, chunk in enumerate(chunks):
        assert chunk.position == i


def test_page_number_preserved_from_source() -> None:
    doc = _make_doc("page one content", "page two content")
    chunker = StructuralChunker(chunk_size=512, overlap=64, encode_fn=_word_encode)
    chunks = chunker.chunk(doc)
    page_numbers = {c.page_number for c in chunks}
    assert page_numbers.issubset({1, 2})


def test_empty_document_returns_empty_list() -> None:
    doc = ExtractedDocument(pages=[])
    chunker = StructuralChunker(chunk_size=512, overlap=64, encode_fn=_word_encode)
    assert chunker.chunk(doc) == []


def test_chunk_is_textchunk_instance() -> None:
    doc = _make_doc("some text here")
    chunker = StructuralChunker(chunk_size=512, overlap=64, encode_fn=_word_encode)
    for chunk in chunker.chunk(doc):
        assert isinstance(chunk, TextChunk)
