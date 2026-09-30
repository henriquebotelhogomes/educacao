"""ADR-018 embedding candidate registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingCandidate:
    alias: str
    model_name: str
    dimension: int
    family: str
    max_sequence_tokens: int

    @property
    def requires_e5_prefix(self) -> bool:
        return self.family == "e5"


CANDIDATES: dict[str, EmbeddingCandidate] = {
    "minilm-l6-v2": EmbeddingCandidate(
        alias="minilm-l6-v2",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        dimension=384,
        family="minilm",
        max_sequence_tokens=256,
    ),
    "e5-small": EmbeddingCandidate(
        alias="e5-small",
        model_name="intfloat/multilingual-e5-small",
        dimension=384,
        family="e5",
        max_sequence_tokens=512,
    ),
    "e5-base": EmbeddingCandidate(
        alias="e5-base",
        model_name="intfloat/multilingual-e5-base",
        dimension=768,
        family="e5",
        max_sequence_tokens=512,
    ),
    "bge-m3": EmbeddingCandidate(
        alias="bge-m3",
        model_name="BAAI/bge-m3",
        dimension=1024,
        family="bge",
        max_sequence_tokens=8192,
    ),
}
