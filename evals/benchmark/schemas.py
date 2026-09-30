"""Typed benchmark configuration and result schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_alias: str
    model_name: str
    model_dimension: int
    dataset_path: str
    manifest_path: str
    output_path: str | None = None
    device: str | None = "cpu"
    offline: bool = False
    chunk_size: int = 512
    chunk_overlap: int = 64
    chunk_tokenizer_name: str = "intfloat/multilingual-e5-small"
    chunking_strategy: str = "structural"
    chunking_strategy_version: str = "structural-v1-t512-o64"
    experiment_type: str = "embedding"
    max_pages_per_document: int | None = None
    max_items: int | None = None
    publish_requested: bool = False

    def deterministic_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude={"output_path", "publish_requested"})
        return payload


class ModelResult(BaseModel):
    alias: str
    model_name: str
    dimension: int
    family: str


class HashSummary(BaseModel):
    config_sha256: str
    dataset_sha256: str
    manifest_sha256: str
    corpus_sha256: str
    document_hashes_sha256: str


class DatasetSummary(BaseModel):
    version: str | None = None
    status: str
    item_count: int
    composition: dict[str, int]
    review_counts: dict[str, int]
    evidence_quote_count: int


class CorpusSummary(BaseModel):
    page_count: int
    chunk_count: int
    chunk_size: int
    chunk_overlap: int
    chunk_tokenizer_name: str = "intfloat/multilingual-e5-small"
    chunking_strategy: str = "structural"
    chunking_strategy_version: str = "structural-v1-t512-o64"
    documents: dict[str, dict[str, int]]


class LatencySummary(BaseModel):
    p50: float = 0.0
    p95: float = 0.0


class UnanswerableTopScores(BaseModel):
    item_id: str
    top_scores: list[float]


class RetrievalSummary(BaseModel):
    evaluated_item_count: int = 0
    unanswerable_item_count: int = 0
    recall_at: dict[str, float] = Field(default_factory=dict)
    precision_at: dict[str, float] = Field(default_factory=dict)
    mrr_at_10: float = 0.0
    ndcg_at_10: float = 0.0
    query_latency_ms: LatencySummary = Field(default_factory=LatencySummary)
    unanswerable_top_scores: list[UnanswerableTopScores] = Field(default_factory=list)
    unanswerable_top_score_summary: LatencySummary = Field(default_factory=LatencySummary)


class TimingSummary(BaseModel):
    extraction_ms: float = 0.0
    chunking_ms: float = 0.0
    corpus_encoding_ms: float = 0.0
    index_build_ms: float = 0.0
    total_ms: float = 0.0


class EmbeddingInputSummary(BaseModel):
    max_sequence_tokens: int
    max_prepared_tokens: int
    truncated_chunk_count: int
    valid: bool


class PublishabilityStatus(BaseModel):
    publishable: bool
    label: str
    blocker_reasons: list[str] = Field(default_factory=list)
    lock_path: str | None = None


class RunMetadata(BaseModel):
    started_at: str
    finished_at: str


class BenchmarkResult(BaseModel):
    schema_version: str = "adr-018-benchmark-result-v1"
    adr: str = "ADR-018"
    experiment_type: str = "embedding"
    model: ModelResult
    config: BenchmarkConfig
    hashes: HashSummary
    dataset: DatasetSummary
    corpus: CorpusSummary
    metrics: RetrievalSummary
    embedding_inputs: EmbeddingInputSummary
    timings: TimingSummary
    publishability: PublishabilityStatus
    run: RunMetadata
