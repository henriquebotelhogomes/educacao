"""Pydantic schemas for the Marco 3.5 golden-dataset (specs/12 §7.3)."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
    pergunta: str = Field(..., description="Question in pt-BR, non-empty")
    resposta_referencia: Optional[str] = Field(
        None,
        description="Reference answer in pt-BR; null for unanswerable items",
    )
    documento: str = Field(..., description="Exact source PDF filename")
    paginas_esperadas: list[int] = Field(
        ...,
        description="1-indexed pages where the answer is found (non-empty)",
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
    def pages_not_empty(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("paginas_esperadas must contain at least one page")
        if any(p < 1 for p in v):
            raise ValueError("page numbers must be >= 1")
        return v

    @field_validator("resposta_referencia")
    @classmethod
    def resposta_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("resposta_referencia must not be blank if provided")
        return v


class DocumentManifestEntry(BaseModel):
    """Provenance record for one source PDF."""

    filename: str
    doc_type: str = Field(
        ...,
        description="narrative | table_heavy | dense | poor_scan",
    )
    sha256: str = Field(..., description="SHA-256 hex digest of the PDF file")
    page_count: int = Field(..., ge=1)
    license_basis: str = Field(
        ...,
        description=(
            "Legal basis for inclusion. "
            "Use 'user_attestation' when authorized by user; "
            "never falsely label as cc/public_domain without evidence."
        ),
    )
    user_attestation: str = Field(
        ...,
        description="Verbatim record of the user authorization statement",
    )
    provenance: str = Field(
        ...,
        description="Original file path relative to repo root",
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
        description="Mapping of PDF filename → SHA-256 (copied from manifest)",
    )
