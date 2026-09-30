"""Typed worker configuration (separate from API settings)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, HttpUrl, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Configuration read once from environment variables or an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MENTORA_",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    service_name: str = "mentora-worker"
    log_level: str = "INFO"

    database_url: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://mentora_app:mentora_dev_only@localhost:5432/mentora"
    )
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")
    qdrant_url: HttpUrl = HttpUrl("http://localhost:6333")

    minio_endpoint: HttpUrl = HttpUrl("http://localhost:9000")
    minio_access_key: str = Field(
        validation_alias=AliasChoices("MENTORA_MINIO_ACCESS_KEY", "MINIO_ROOT_USER")
    )
    minio_secret_key: SecretStr = Field(
        validation_alias=AliasChoices("MENTORA_MINIO_SECRET_KEY", "MINIO_ROOT_PASSWORD")
    )
    minio_bucket: str = Field(
        default="mentora-dev",
        validation_alias=AliasChoices("MENTORA_MINIO_BUCKET", "MINIO_BUCKET"),
    )

    ingestion_stream: str = "mentora:ingestion"
    ingestion_consumer_group: str = "workers"
    ingestion_consumer_name: str = "worker-0"
    ingestion_dlq_stream: str = "mentora:ingestion:dlq"
    stream_block_ms: int = 5000
    stream_max_retries: int = 3
    autoclaim_min_idle_ms: int = 30_000

    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_model_version: str = "v1"
    embedding_dim: int = 384
    embedding_batch_size: int = 32

    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64
    chunking_strategy_version: str = "structural-v1-t512-o64"
    free_document_max_pages: int = 50

    outbox_poll_interval_seconds: float = 1.0
    outbox_batch_size: int = 50


@lru_cache
def get_settings() -> WorkerSettings:
    """Return the process-wide immutable settings instance."""
    return WorkerSettings()  # type: ignore[call-arg]
