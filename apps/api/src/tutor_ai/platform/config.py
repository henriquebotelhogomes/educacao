"""Typed application configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, HttpUrl, PostgresDsn, RedisDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration read once from environment variables or an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MENTORA_",
        case_sensitive=False,
        extra="ignore",
    )

    app_version: str = "0.1.0"
    environment: str = "development"
    service_name: str = "mentora-api"
    log_level: str = "INFO"
    telemetry_enabled: bool = True
    jwt_secret: SecretStr
    access_token_minutes: int = 20
    refresh_token_days: int = 7
    cookie_secure: bool = True
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None
    google_oauth_redirect_uri: HttpUrl | None = None
    readiness_check_dependencies: bool = True
    readiness_timeout_seconds: float = 1.0

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
    document_max_size_bytes: int = 10 * 1024 * 1024
    free_document_limit: int = 3
    groq_api_key: SecretStr | None = None
    groq_chat_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: HttpUrl = HttpUrl("https://openrouter.ai/api/v1")
    openrouter_chat_model: str = "deepseek/deepseek-chat"
    tutor_retrieval_limit: int = 5
    tutor_min_retrieval_score: float = 0.5
    free_tutor_questions_per_month: int = 30
    otel_exporter_otlp_endpoint: HttpUrl = HttpUrl("http://localhost:4318")

    @model_validator(mode="after")
    def validate_cookie_security(self) -> "Settings":
        """Prevent an HTTP-safe development override from reaching hosted environments."""
        if self.environment not in {"development", "test"} and not self.cookie_secure:
            raise ValueError("MENTORA_COOKIE_SECURE must be true outside development or test")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""
    return Settings()  # type: ignore[call-arg]
