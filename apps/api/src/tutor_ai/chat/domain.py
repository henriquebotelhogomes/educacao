"""Tutor conversation domain types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ConfidenceBand(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: UUID
    document_version_id: UUID
    page_number: int
    snippet: str
    score: float


@dataclass(frozen=True)
class CitationCandidate:
    chunk: RetrievedChunk


@dataclass(frozen=True)
class TutorResult:
    content: str
    grounded: bool
    confidence_band: ConfidenceBand
    fallback_reason: str | None
    citations: list[CitationCandidate]
    model: str | None
