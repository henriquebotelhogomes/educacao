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
        assert count == EXPECTED_ANSWERABLE, (
            f"Expected {EXPECTED_ANSWERABLE} answerable items, got {count}"
        )

    def test_unanswerable_count(self, golden_items: list[dict]) -> None:
        count = sum(1 for i in golden_items if i["tipo"] == "unanswerable")
        assert count == EXPECTED_UNANSWERABLE, (
            f"Expected {EXPECTED_UNANSWERABLE} unanswerable items, got {count}"
        )

    def test_ambiguous_partial_count(self, golden_items: list[dict]) -> None:
        count = sum(1 for i in golden_items if i["tipo"] == "ambiguous_partial")
        assert count == EXPECTED_AMBIGUOUS_PARTIAL, (
            f"Expected {EXPECTED_AMBIGUOUS_PARTIAL} ambiguous_partial items, got {count}"
        )

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
        """Each document must have exactly ITEMS_PER_DOC items."""
        from collections import Counter

        counts = Counter(i["documento"] for i in golden_items)
        for filename in EXPECTED_FILENAMES:
            assert counts[filename] == ITEMS_PER_DOC, (
                f"{filename}: expected {ITEMS_PER_DOC} items, got {counts[filename]}"
            )

    def test_pages_within_document_bounds(self, golden_items: list[dict]) -> None:
        """All paginas_esperadas values must be within the actual page count."""
        for item in golden_items:
            doc = item["documento"]
            max_page = EXPECTED_PAGE_COUNTS[doc]
            for page in item["paginas_esperadas"]:
                assert 1 <= page <= max_page, (
                    f"Item {item['id']}: page {page} out of range for {doc} (max {max_page})"
                )


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
        """No item should be pre-marked as reviewed/approved (prevents fabrication)."""
        for item in golden_items:
            assert item["review_status"] == "draft", (
                f"Item {item['id']}: review_status must be 'draft' until human review, "
                f"got '{item['review_status']}'"
            )

    def test_unanswerable_items_have_null_or_explanation(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            if item["tipo"] == "unanswerable":
                assert item.get("resposta_referencia") is None, (
                    f"Item {item['id']}: unanswerable items must have null resposta_referencia"
                )

    def test_answerable_items_have_reference_answer(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            if item["tipo"] == "answerable":
                ref = item.get("resposta_referencia")
                assert ref is not None and ref.strip(), (
                    f"Item {item['id']}: answerable items must have a non-empty resposta_referencia"
                )

    def test_unanswerable_items_have_notas(self, golden_items: list[dict]) -> None:
        """Unanswerable items must explain why they are unanswerable."""
        for item in golden_items:
            if item["tipo"] == "unanswerable":
                notas = item.get("notas")
                assert notas and notas.strip(), (
                    f"Item {item['id']}: unanswerable items must have notas explaining why"
                )

    def test_all_perguntas_are_nonempty_ptbr(self, golden_items: list[dict]) -> None:
        for item in golden_items:
            assert item["pergunta"].strip(), f"Item {item['id']}: empty pergunta"
            assert len(item["pergunta"]) >= 10, (
                f"Item {item['id']}: pergunta too short: {item['pergunta']!r}"
            )

    def test_difficulty_values_valid(self, golden_items: list[dict]) -> None:
        valid = {"facil", "medio", "dificil"}
        for item in golden_items:
            assert item["dificuldade"] in valid, (
                f"Item {item['id']}: invalid dificuldade '{item['dificuldade']}'"
            )

    def test_difficulty_balanced_across_items(self, golden_items: list[dict]) -> None:
        """Each difficulty level should appear in at least 20% of items."""
        from collections import Counter

        counts = Counter(i["dificuldade"] for i in golden_items)
        min_expected = int(TOTAL_ITEMS * 0.20)
        for level in ("facil", "medio", "dificil"):
            assert counts[level] >= min_expected, (
                f"Difficulty '{level}' has only {counts[level]} items, "
                f"expected at least {min_expected}"
            )
