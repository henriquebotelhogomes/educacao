"""Tests for evals/datasets/v1/golden.jsonl composition and schema validity."""

from __future__ import annotations

from evals.schema import GoldenItem
from evals.tests.conftest import (
    EXPECTED_AMBIGUOUS_PARTIAL,
    EXPECTED_ANSWERABLE,
    EXPECTED_FILENAMES,
    EXPECTED_PAGE_COUNTS,
    EXPECTED_UNANSWERABLE,
    ITEMS_PER_DOC,
    TOTAL_ITEMS,
)


class TestGoldenDatasetSize:
    def test_exactly_120_items(self, golden_items: list[dict]) -> None:
        assert len(golden_items) == TOTAL_ITEMS

    def test_answerable_count(self, golden_items: list[dict]) -> None:
        count = sum(1 for i in golden_items if i["tipo"] == "answerable")
        assert count == EXPECTED_ANSWERABLE

    def test_unanswerable_count(self, golden_items: list[dict]) -> None:
        count = sum(1 for i in golden_items if i["tipo"] == "unanswerable")
        assert count == EXPECTED_UNANSWERABLE

    def test_ambiguous_partial_count(self, golden_items: list[dict]) -> None:
        count = sum(1 for i in golden_items if i["tipo"] == "ambiguous_partial")
        assert count == EXPECTED_AMBIGUOUS_PARTIAL

    def test_composition_sums_to_total(self, golden_items: list[dict]) -> None:
        answerable = sum(1 for i in golden_items if i["tipo"] == "answerable")
        unanswerable = sum(1 for i in golden_items if i["tipo"] == "unanswerable")
        ambiguous = sum(1 for i in golden_items if i["tipo"] == "ambiguous_partial")
        assert answerable + unanswerable + ambiguous == TOTAL_ITEMS


class TestGoldenDatasetDocumentCoverage:
    def test_all_six_documents_referenced(self, golden_items: list[dict]) -> None:
        docs_used = {i["documento"] for i in golden_items}
        assert docs_used == EXPECTED_FILENAMES

    def test_balanced_coverage_per_document(self, golden_items: list[dict]) -> None:
        from collections import Counter

        counts = Counter(i["documento"] for i in golden_items)
        for filename in EXPECTED_FILENAMES:
            assert (
                counts[filename] == ITEMS_PER_DOC
            ), f"{filename}: expected {ITEMS_PER_DOC} items, got {counts[filename]}"

    def test_balanced_composition_per_document(self, golden_items: list[dict]) -> None:
        """Each document must have 12 answerable + 5 unanswerable + 3 ambiguous."""
        from collections import Counter, defaultdict

        per_doc: dict[str, Counter] = defaultdict(Counter)
        for item in golden_items:
            per_doc[item["documento"]][item["tipo"]] += 1
        for filename in EXPECTED_FILENAMES:
            counts = per_doc[filename]
            assert counts["answerable"] == 12, f"{filename}: {counts}"
            assert counts["unanswerable"] == 5, f"{filename}: {counts}"
            assert counts["ambiguous_partial"] == 3, f"{filename}: {counts}"

    def test_pages_within_document_bounds(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            doc = item["documento"]
            max_page = EXPECTED_PAGE_COUNTS[doc]
            for page in item["paginas_esperadas"]:
                assert (
                    1 <= page <= max_page
                ), f"Item {item['id']}: page {page} out of range for {doc} (max {max_page})"


class TestGoldenDatasetItemSchema:
    def test_all_items_parse_as_golden_item(self, golden_items: list[dict]) -> None:
        for raw in golden_items:
            GoldenItem(**raw)

    def test_all_ids_unique(self, golden_items: list[dict]) -> None:
        ids = [i["id"] for i in golden_items]
        assert len(ids) == len(set(ids)), "Duplicate IDs found"

    def test_all_ids_start_with_v1(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            assert item["id"].startswith("v1-"), f"ID {item['id']} must start with 'v1-'"

    def test_all_review_status_is_draft(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            assert (
                item["review_status"] == "draft"
            ), f"Item {item['id']}: review_status must be 'draft' until human review"


class TestGoldenDatasetEvidence:
    def test_answerable_have_evidence_and_pages(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            if item["tipo"] == "answerable":
                assert item["evidence_quotes"], f"{item['id']}: missing evidence_quotes"
                assert item["paginas_esperadas"], f"{item['id']}: missing paginas_esperadas"
                ref = item.get("resposta_referencia")
                assert ref and ref.strip(), f"{item['id']}: missing resposta_referencia"

    def test_ambiguous_have_evidence_pages_and_notas(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            if item["tipo"] == "ambiguous_partial":
                assert item["evidence_quotes"], f"{item['id']}: missing evidence_quotes"
                assert item["paginas_esperadas"], f"{item['id']}: missing paginas_esperadas"
                assert item.get("notas", "").strip(), f"{item['id']}: missing notas"

    def test_unanswerable_have_empty_pages_and_evidence(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            if item["tipo"] == "unanswerable":
                assert (
                    item.get("resposta_referencia") is None
                ), f"{item['id']}: unanswerable must have null resposta_referencia"
                assert (
                    item["paginas_esperadas"] == []
                ), f"{item['id']}: unanswerable must have empty paginas_esperadas"
                assert (
                    item["evidence_quotes"] == []
                ), f"{item['id']}: unanswerable must have empty evidence_quotes"
                assert item.get(
                    "notas", ""
                ).strip(), f"{item['id']}: unanswerable must explain why in notas"

    def test_evidence_quotes_are_nontrivial(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            for quote in item["evidence_quotes"]:
                assert (
                    len(quote.strip()) >= 15
                ), f"{item['id']}: evidence quote too short: {quote!r}"


class TestGoldenDatasetQuestions:
    def test_all_perguntas_are_nonempty(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            assert item["pergunta"].strip(), f"Item {item['id']}: empty pergunta"
            assert (
                len(item["pergunta"]) >= 10
            ), f"Item {item['id']}: pergunta too short: {item['pergunta']!r}"

    def test_questions_are_not_cloze_tautologies(self, golden_items: list[dict]) -> None:
        """Reject 'what does this sentence say' style non-questions."""
        banned = [
            "o que esta frase",
            "o que essa frase",
            "complete a frase",
            "preencha a lacuna",
            "qual palavra falta",
        ]
        for item in golden_items:
            low = item["pergunta"].lower()
            for phrase in banned:
                assert phrase not in low, f"{item['id']}: cloze/tautology question: {low!r}"

    def test_difficulty_values_valid(self, golden_items: list[dict]) -> None:
        valid = {"facil", "medio", "dificil"}
        for item in golden_items:
            assert (
                item["dificuldade"] in valid
            ), f"Item {item['id']}: invalid dificuldade '{item['dificuldade']}'"

    def test_difficulty_balanced_across_items(self, golden_items: list[dict]) -> None:
        from collections import Counter

        counts = Counter(i["dificuldade"] for i in golden_items)
        min_expected = int(TOTAL_ITEMS * 0.20)
        for level in ("facil", "medio", "dificil"):
            assert counts[level] >= min_expected, (
                f"Difficulty '{level}' has only {counts[level]} items, "
                f"expected at least {min_expected}"
            )
