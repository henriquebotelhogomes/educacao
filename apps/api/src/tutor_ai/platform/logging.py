"""Structured logging and request correlation."""

from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

from tutor_ai.platform.config import Settings

request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)


def get_trace_id() -> str | None:
    """Return the active W3C-compatible OpenTelemetry trace ID when sampled."""
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return format(span_context.trace_id, "032x")


class JsonFormatter(logging.Formatter):
    """Emit only JSON records so logs are parsable by collectors."""

    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self._service_name = service_name
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": self._service_name,
            "environment": self._environment,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
            "trace_id": get_trace_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    """Set the root logger once with the platform JSON formatter."""
    root_logger = logging.getLogger()
    if getattr(root_logger, "_mentora_configured", False):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(settings.service_name, settings.environment))
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.log_level.upper())
    root_logger._mentora_configured = True  # type: ignore[attr-defined]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request and trace correlation IDs to each API response and log."""

    def __init__(self, app: Any, service_name: str) -> None:
        super().__init__(app)
        self._logger = logging.getLogger(service_name)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        token = request_id_context.set(request_id)
        request.state.request_id = request_id
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            self._logger.info(
                "http.request.completed method=%s path=%s duration_ms=%s",
                request.method,
                request.url.path,
                duration_ms,
            )
            request_id_context.reset(token)

        response.headers["x-request-id"] = request_id
        trace_id = get_trace_id()
        if trace_id:
            response.headers["x-trace-id"] = trace_id
        return response
