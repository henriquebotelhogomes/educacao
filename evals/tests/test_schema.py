"""Tests for evals/schema.py — Pydantic models (no data files required)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evals.schema import (
    DatasetManifest,
    Difficulty,
    DocumentManifestEntry,
    GoldenItem,
    ItemType,
    LockManifest,
    ReviewStatus,
)

_VALID_DOC_ENTRY: dict[str, object] = {
    "filename": "test.pdf",
    "doc_type": "narrative",
    "sha256": "a" * 64,
    "page_count": 100,
    "corpus_path": "support/ebooks/test.pdf",
    "license_basis": "user_attestation",
    "user_attestation": "Attested by user on 2026-08-03",
    "provenance": "support/ebooks/test.pdf",
}

_VALID_ITEM: dict[str, object] = {
    "id": "v1-ha-001",
    "pergunta": "Qual é a origem histórica da questão agrária no Brasil?",
    "resposta_referencia": "A questão agrária refere-se à concentração da terra.",
    "documento": "História Agrária.pdf",
    "paginas_esperadas": [10, 11],
    "evidence_quotes": ["a concentração da terra é histórica"],
    "tipo": "answerable",
    "dificuldade": "facil",
    "review_status": "draft",
}

_VALID_UNANSWERABLE: dict[str, object] = {
    "id": "v1-ha-016",
    "pergunta": "Qual é a taxa de juros do PRONAF na safra 2025/2026?",
    "resposta_referencia": None,
    "documento": "História Agrária.pdf",
    "paginas_esperadas": [],
    "evidence_quotes": [],
    "tipo": "unanswerable",
    "dificuldade": "facil",
    "review_status": "draft",
    "notas": "A obra é historiográfica e não traz taxas de crédito atuais.",
}

_VALID_AMBIGUOUS: dict[str, object] = {
    "id": "v1-ha-013",
    "pergunta": "As políticas de imigração europeia substituíram a mão de obra escrava?",
    "resposta_referencia": "O texto só afirma que não lograram êxito.",
    "documento": "História Agrária.pdf",
    "paginas_esperadas": [160],
    "evidence_quotes": ["estas não haviam logrado êxitos"],
    "tipo": "ambiguous_partial",
    "dificuldade": "medio",
    "review_status": "draft",
    "notas": "Parcial: comenta a falta de êxito, mas não o desfecho geral.",
}


class TestGoldenItemAnswerable:
    def test_valid_answerable(self) -> None:
        item = GoldenItem.model_validate(_VALID_ITEM)
        assert item.tipo == ItemType.ANSWERABLE
        assert item.review_status == ReviewStatus.DRAFT
        assert item.evidence_quotes

    def test_all_difficulty_values(self) -> None:
        for diff in ("facil", "medio", "dificil"):
            item = GoldenItem.model_validate({**_VALID_ITEM, "dificuldade": diff})
            assert item.dificuldade == Difficulty(diff)

    def test_answerable_requires_evidence(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "evidence_quotes": []})

    def test_answerable_requires_pages(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "paginas_esperadas": []})

    def test_answerable_requires_reference_answer(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "resposta_referencia": None})

    def test_blank_resposta_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "resposta_referencia": "   "})

    def test_blank_evidence_quote_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "evidence_quotes": ["   "]})


class TestGoldenItemUnanswerable:
    def test_valid_unanswerable(self) -> None:
        item = GoldenItem.model_validate(_VALID_UNANSWERABLE)
        assert item.resposta_referencia is None
        assert item.paginas_esperadas == []
        assert item.evidence_quotes == []

    def test_unanswerable_with_answer_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_UNANSWERABLE, "resposta_referencia": "algo"})

    def test_unanswerable_with_pages_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_UNANSWERABLE, "paginas_esperadas": [5]})

    def test_unanswerable_with_evidence_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate(
                {**_VALID_UNANSWERABLE, "evidence_quotes": ["qualquer coisa"]}
            )

    def test_unanswerable_without_notas_rejected(self) -> None:
        data = {**_VALID_UNANSWERABLE}
        data["notas"] = None
        with pytest.raises(ValidationError):
            GoldenItem.model_validate(data)


class TestGoldenItemAmbiguous:
    def test_valid_ambiguous(self) -> None:
        item = GoldenItem.model_validate(_VALID_AMBIGUOUS)
        assert item.tipo == ItemType.AMBIGUOUS_PARTIAL

    def test_ambiguous_requires_notas(self) -> None:
        data = {**_VALID_AMBIGUOUS}
        data["notas"] = None
        with pytest.raises(ValidationError):
            GoldenItem.model_validate(data)

    def test_ambiguous_requires_evidence(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_AMBIGUOUS, "evidence_quotes": []})

    def test_ambiguous_requires_pages(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_AMBIGUOUS, "paginas_esperadas": []})


class TestGoldenItemCommon:
    def test_empty_pergunta_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "pergunta": "   "})

    def test_zero_page_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "paginas_esperadas": [0]})

    def test_invalid_tipo_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "tipo": "unknown"})

    def test_invalid_dificuldade_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "dificuldade": "extreme"})

    def test_review_status_defaults_to_draft(self) -> None:
        data = {k: v for k, v in _VALID_ITEM.items() if k != "review_status"}
        item = GoldenItem.model_validate(data)
        assert item.review_status == ReviewStatus.DRAFT


class TestDocumentManifestEntry:
    def test_valid_entry(self) -> None:
        entry = DocumentManifestEntry.model_validate(_VALID_DOC_ENTRY)
        assert entry.doc_type == "narrative"
        assert entry.license_basis == "user_attestation"
        assert entry.corpus_path == "support/ebooks/test.pdf"

    def test_corpus_path_required(self) -> None:
        data = {k: v for k, v in _VALID_DOC_ENTRY.items() if k != "corpus_path"}
        with pytest.raises(ValidationError):
            DocumentManifestEntry.model_validate(data)

    def test_page_count_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            DocumentManifestEntry.model_validate({**_VALID_DOC_ENTRY, "page_count": 0})

    def test_derived_fixture_fields_optional(self) -> None:
        entry = DocumentManifestEntry.model_validate(
            {
                **_VALID_DOC_ENTRY,
                "fixture_path": "evals/fixtures/x.pdf",
                "source_sha256": "b" * 64,
                "page_map": {"1": 18, "2": 20},
            }
        )
        assert entry.page_map == {"1": 18, "2": 20}


class TestDatasetManifest:
    def test_valid_manifest(self) -> None:
        manifest = DatasetManifest(
            version="v1",
            status="draft",
            created_at="2026-08-03T00:00:00Z",
            spec_reference="specs/12 §7.3",
            attested_on="2026-08-03",
            documents=[DocumentManifestEntry.model_validate(_VALID_DOC_ENTRY)],
            dataset_file="golden.jsonl",
            item_count=120,
            composition={
                "answerable": 72,
                "unanswerable": 30,
                "ambiguous_partial": 18,
            },
        )
        assert manifest.status == "draft"

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DatasetManifest(
                version="v1",
                status="pending",
                created_at="2026-08-03T00:00:00Z",
                spec_reference="specs/12 §7.3",
                attested_on="2026-08-03",
                documents=[],
                dataset_file="golden.jsonl",
                item_count=120,
                composition={
                    "answerable": 72,
                    "unanswerable": 30,
                    "ambiguous_partial": 18,
                },
            )

    def test_composition_wrong_keys_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DatasetManifest(
                version="v1",
                status="draft",
                created_at="2026-08-03T00:00:00Z",
                spec_reference="specs/12 §7.3",
                attested_on="2026-08-03",
                documents=[],
                dataset_file="golden.jsonl",
                item_count=120,
                composition={"answerable": 120},
            )


class TestLockManifest:
    def test_valid_lock(self) -> None:
        lock = LockManifest(
            version="v1",
            locked_at="2026-08-03T12:00:00Z",
            dataset_sha256="b" * 64,
            manifest_sha256="c" * 64,
            item_count=120,
            composition={
                "answerable": 72,
                "unanswerable": 30,
                "ambiguous_partial": 18,
            },
            document_hashes={"test.pdf": "a" * 64},
        )
        assert lock.item_count == 120
