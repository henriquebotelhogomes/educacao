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

_VALID_DOC_ENTRY = {
    "filename": "test.pdf",
    "doc_type": "narrative",
    "sha256": "a" * 64,
    "page_count": 100,
    "license_basis": "user_attestation",
    "user_attestation": "Attested by user on 2026-08-03",
    "provenance": "support/ebooks/test.pdf",
}

_VALID_ITEM = {
    "id": "v1-ha-001",
    "pergunta": "O que é a questão agrária?",
    "resposta_referencia": "A questão agrária refere-se à distribuição da terra.",
    "documento": "História Agrária.pdf",
    "paginas_esperadas": [10, 11],
    "tipo": "answerable",
    "dificuldade": "facil",
    "review_status": "draft",
}


class TestGoldenItem:
    def test_valid_answerable(self) -> None:
        item = GoldenItem.model_validate(_VALID_ITEM)
        assert item.tipo == ItemType.ANSWERABLE
        assert item.review_status == ReviewStatus.DRAFT

    def test_valid_unanswerable_null_resposta(self) -> None:
        data = {**_VALID_ITEM, "tipo": "unanswerable", "resposta_referencia": None}
        item = GoldenItem.model_validate(data)
        assert item.resposta_referencia is None

    def test_valid_ambiguous_partial(self) -> None:
        data = {
            **_VALID_ITEM,
            "tipo": "ambiguous_partial",
            "resposta_referencia": "Parcialmente: ...",
        }
        item = GoldenItem.model_validate(data)
        assert item.tipo == ItemType.AMBIGUOUS_PARTIAL

    def test_all_difficulty_values(self) -> None:
        for diff in ("facil", "medio", "dificil"):
            item = GoldenItem.model_validate({**_VALID_ITEM, "dificuldade": diff})
            assert item.dificuldade == Difficulty(diff)

    def test_empty_pergunta_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "pergunta": "   "})

    def test_empty_pages_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "paginas_esperadas": []})

    def test_zero_page_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "paginas_esperadas": [0]})

    def test_blank_resposta_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate({**_VALID_ITEM, "resposta_referencia": "   "})

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

    def test_notas_optional(self) -> None:
        item = GoldenItem.model_validate(_VALID_ITEM)
        assert item.notas is None


class TestDocumentManifestEntry:
    def test_valid_entry(self) -> None:
        entry = DocumentManifestEntry.model_validate(_VALID_DOC_ENTRY)
        assert entry.doc_type == "narrative"
        assert entry.license_basis == "user_attestation"

    def test_page_count_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            DocumentManifestEntry.model_validate({**_VALID_DOC_ENTRY, "page_count": 0})


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
