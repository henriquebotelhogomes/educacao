"""Double-submit CSRF middleware for browser cookie sessions."""

from __future__ import annotations

import hmac
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from tutor_ai.platform.logging import get_trace_id
from tutor_ai.platform.schemas import ErrorResponse

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CSRFMiddleware(BaseHTTPMiddleware):
    """Require the readable CSRF cookie value in a request header for mutations."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)

        cookie_value = request.cookies.get("mentora_csrf")
        header_value = request.headers.get("x-csrf-token")
        if cookie_value and header_value and hmac.compare_digest(cookie_value, header_value):
            return await call_next(request)

        error = ErrorResponse(
            code="csrf_invalid",
            message="O token CSRF está ausente ou inválido.",
            request_id=getattr(request.state, "request_id", None),
            trace_id=get_trace_id(),
        )
        return JSONResponse(status_code=403, content=error.model_dump())
