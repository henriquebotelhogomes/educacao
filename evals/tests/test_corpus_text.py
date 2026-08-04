"""Tests for evals/corpus_text.py normalization and quote matching."""

from __future__ import annotations

from evals.corpus_text import clean_text, normalize_for_match, quote_present


class TestCleanText:
    def test_joins_hyphenated_linebreak(self) -> None:
        assert clean_text("agri-\ncultura familiar") == "agricultura familiar"

    def test_collapses_whitespace(self) -> None:
        assert clean_text("a   b\t\nc") == "a b c"

    def test_strips_junk_chars(self) -> None:
        assert clean_text("caf\u00ade\u200b") == "cafe"

    def test_preserves_case_and_accents(self) -> None:
        assert clean_text("Água É Vida") == "Água É Vida"


class TestQuoteMatching:
    def test_case_insensitive_match(self) -> None:
        page = "A ampliação da produção de café foi expressiva."
        assert quote_present("A AMPLIAÇÃO DA PRODUÇÃO DE CAFÉ", page)

    def test_whitespace_insensitive_match(self) -> None:
        page = "linha um\nlinha  dois   três"
        assert quote_present("linha um linha dois três", page)

    def test_absent_quote_not_matched(self) -> None:
        page = "conteúdo real da página"
        assert not quote_present("frase que não existe", page)

    def test_empty_quote_not_matched(self) -> None:
        assert not quote_present("", "qualquer conteúdo")

    def test_normalize_for_match_is_casefolded(self) -> None:
        assert normalize_for_match("Água") == "água"
