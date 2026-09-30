"""Public DTOs for the versioned API."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Consistent response format for API failures."""

    code: str
    message: str
    details: dict[str, object] | None = None
    request_id: str | None = None
    trace_id: str | None = None


class MetaResponse(BaseModel):
    """Minimal stable API contract for Marco 0."""

    version: str
    environment: str
    service: str
    trace_id: str | None = None


class ReadinessResponse(BaseModel):
    """Current readiness and checked dependency names."""

    status: str
    dependencies: list[str]
