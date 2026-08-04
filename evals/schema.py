"""Pydantic schemas for the Marco 3.5 golden-dataset (specs/12 §7.3).

The :class:`GoldenItem` model enforces *conditional* invariants keyed on
``tipo`` so the dataset cannot drift into a semantically untrustworthy state:

* ``answerable`` — requires a reference answer, at least one expected page and
  at least one verbatim ``evidence_quotes`` entry.
* ``unanswerable`` — requires a null reference answer, **empty** pages and
  evidence, plus a ``notas`` rationale explaining why the corpus cannot answer.
* ``ambiguous_partial`` — requires reference/pages/evidence *and* ``notas``
  describing the partiality.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ItemType(str, Enum):
    ANSWERABLE = "answerable"
    UNANSWERABLE = "unanswerable"
    AMBIGUOUS_PARTIAL = "ambiguous_partial"


class Difficulty(str, Enum):
    FACIL = "facil"
    MEDIO = "medio"
    DIFICIL = "dificil"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"


class GoldenItem(BaseModel):
    """One entry in the golden dataset (specs/12 §7.3)."""

    id: str = Field(..., description="Stable unique ID: v1-{doc}-{NNN}")
    pergunta: str = Field(..., description="Natural pt-BR question, non-empty")
    resposta_referencia: Optional[str] = Field(
        None,
        description="Reference answer in pt-BR; null for unanswerable items",
    )
    documento: str = Field(..., description="Logical document name from the manifest")
    paginas_esperadas: list[int] = Field(
        default_factory=list,
        description="1-indexed pages where the answer is grounded; empty for unanswerable",
    )
    evidence_quotes: list[str] = Field(
        default_factory=list,
        description="Verbatim snippets copied from paginas_esperadas; empty for unanswerable",
    )
    tipo: ItemType
    dificuldade: Difficulty
    review_status: ReviewStatus = Field(
        ReviewStatus.DRAFT,
        description="draft until human-reviewed; never fabricate as approved",
    )
    notas: Optional[str] = Field(
        None,
        description="Rationale for unanswerable/ambiguous classification",
    )

    @field_validator("pergunta")
    @classmethod
    def pergunta_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("pergunta must not be empty")
        return v

    @field_validator("paginas_esperadas")
    @classmethod
    def pages_positive(cls, v: list[int]) -> list[int]:
        if any(p < 1 for p in v):
            raise ValueError("page numbers must be >= 1")
        return v

    @field_validator("evidence_quotes")
    @classmethod
    def quotes_not_blank(cls, v: list[str]) -> list[str]:
        for quote in v:
            if not quote.strip():
                raise ValueError("evidence_quotes entries must not be blank")
        return v

    @model_validator(mode="after")
    def check_conditional_invariants(self) -> GoldenItem:
        has_answer = bool(self.resposta_referencia and self.resposta_referencia.strip())
        has_pages = bool(self.paginas_esperadas)
        has_evidence = bool(self.evidence_quotes)
        has_notas = bool(self.notas and self.notas.strip())

        if self.tipo == ItemType.ANSWERABLE:
            if not has_answer:
                raise ValueError("answerable items require a non-empty resposta_referencia")
            if not has_pages:
                raise ValueError("answerable items require at least one pagina_esperada")
            if not has_evidence:
                raise ValueError("answerable items require at least one evidence_quote")
        elif self.tipo == ItemType.UNANSWERABLE:
            if has_answer:
                raise ValueError("unanswerable items must have a null resposta_referencia")
            if has_pages:
                raise ValueError("unanswerable items must have empty paginas_esperadas")
            if has_evidence:
                raise ValueError("unanswerable items must have empty evidence_quotes")
            if not has_notas:
                raise ValueError("unanswerable items require notas explaining why")
        elif self.tipo == ItemType.AMBIGUOUS_PARTIAL:
            if not has_answer:
                raise ValueError("ambiguous_partial items require a resposta_referencia")
            if not has_pages:
                raise ValueError("ambiguous_partial items require at least one pagina_esperada")
            if not has_evidence:
                raise ValueError("ambiguous_partial items require at least one evidence_quote")
            if not has_notas:
                raise ValueError("ambiguous_partial items require notas describing the partiality")
        return self


class DocumentManifestEntry(BaseModel):
    """Provenance record for one logical corpus document."""

    filename: str = Field(..., description="Logical document name referenced by golden items")
    doc_type: str = Field(..., description="narrative | table_heavy | dense | poor_scan")
    sha256: str = Field(..., description="SHA-256 of the logical document file")
    page_count: int = Field(..., ge=1, description="Page count of the logical document")
    corpus_path: str = Field(
        ...,
        description=(
            "Repo-relative path to the text-extractable PDF used by the evidence "
            "audit. For a derived poor-scan fixture this points at the original "
            "text source, not the image-only fixture."
        ),
    )
    license_basis: str = Field(
        ...,
        description=(
            "Legal basis for inclusion. Use 'user_attestation' when authorized by "
            "user; never falsely label as cc/public_domain without evidence."
        ),
    )
    user_attestation: str = Field(
        ...,
        description="Verbatim record of the user authorization statement",
    )
    provenance: str = Field(
        ...,
        description="Original source file path relative to repo root",
    )
    fixture_path: Optional[str] = Field(
        None,
        description="For derived fixtures: repo-relative path to the fixture file",
    )
    source_sha256: Optional[str] = Field(
        None,
        description="For derived fixtures: SHA-256 of the original source PDF",
    )
    page_map: Optional[dict[str, int]] = Field(
        None,
        description=(
            "For derived fixtures: mapping of logical (fixture) page -> original "
            "source page, so evidence can be audited against corpus_path."
        ),
    )


class DatasetManifest(BaseModel):
    """Top-level manifest for evals/datasets/v1/."""

    version: str = Field(..., description="Dataset version string, e.g. 'v1'")
    status: str = Field(
        ...,
        description="'draft' until every item reaches review_status=approved",
    )
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    spec_reference: str = Field(..., description="Spec section that defines this dataset")
    attested_on: str = Field(..., description="ISO-8601 date of user authorization")
    documents: list[DocumentManifestEntry]
    dataset_file: str = Field(..., description="Filename of the JSONL dataset")
    item_count: int = Field(..., ge=120)
    composition: dict[str, int] = Field(
        ...,
        description="{'answerable': N, 'unanswerable': N, 'ambiguous_partial': N}",
    )

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        allowed = {"draft", "frozen", "deprecated"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

    @field_validator("composition")
    @classmethod
    def composition_keys(cls, v: dict[str, int]) -> dict[str, int]:
        required = {"answerable", "unanswerable", "ambiguous_partial"}
        if set(v.keys()) != required:
            raise ValueError(f"composition must have exactly keys {required}")
        return v


class LockManifest(BaseModel):
    """Written by 'validate freeze'; proves dataset hasn't changed since measurement."""

    version: str
    locked_at: str = Field(..., description="ISO-8601 timestamp when freeze was run")
    dataset_sha256: str
    manifest_sha256: str
    item_count: int
    composition: dict[str, int]
    document_hashes: dict[str, str] = Field(
        ...,
        description="Mapping of logical document filename → SHA-256 (copied from manifest)",
    )
