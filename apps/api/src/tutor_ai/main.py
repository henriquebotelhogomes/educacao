"""FastAPI application factory for the Mentora AI platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from redis import Redis

from tutor_ai.ai.retrieval import QdrantRetriever
from tutor_ai.ai.tutor import TutorService
from tutor_ai.chat.api import feedback_router
from tutor_ai.chat.api import router as chat_router
from tutor_ai.classes.api import router as classes_router
from tutor_ai.documents.api import router as documents_router
from tutor_ai.documents.storage import DocumentStorage
from tutor_ai.identity.api import router as identity_router
from tutor_ai.identity.sessions import SessionStore
from tutor_ai.platform.config import Settings, get_settings
from tutor_ai.platform.csrf import CSRFMiddleware
from tutor_ai.platform.errors import ApiError
from tutor_ai.platform.health import DependencyChecker
from tutor_ai.platform.logging import RequestContextMiddleware, configure_logging, get_trace_id
from tutor_ai.platform.schemas import ErrorResponse, MetaResponse, ReadinessResponse
from tutor_ai.platform.telemetry import configure_tracing
from tutor_ai.tenancy.api import router as tenancy_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        app.state.redis.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API without business-domain features."""
    app_settings = settings or get_settings()
    configure_logging(app_settings)

    app = FastAPI(
        title="Mentora AI API",
        version=app_settings.app_version,
        description="API versionada do Mentora AI.",
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = app_settings
    app.state.dependency_checker = DependencyChecker(app_settings)
    app.state.redis = Redis.from_url(str(app_settings.redis_url), decode_responses=True)
    app.state.session_store = SessionStore(
        app.state.redis,
        timedelta(days=app_settings.refresh_token_days),
    )
    app.state.document_storage = DocumentStorage(app_settings)
    app.state.tutor_service = TutorService(
        app_settings,
        QdrantRetriever(
            str(app_settings.qdrant_url),
            "intfloat/multilingual-e5-small",
            "multilingual-e5-small_v1",
            app_settings.tutor_retrieval_limit,
        ),
    )

    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RequestContextMiddleware, service_name=app_settings.service_name)
    configure_tracing(app, app_settings)

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        error = ErrorResponse(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=getattr(request.state, "request_id", None),
            trace_id=get_trace_id(),
        )
        return JSONResponse(status_code=exc.status_code, content=error.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        error = ErrorResponse(
            code="internal_error",
            message="Ocorreu um erro interno.",
            details={"type": type(exc).__name__},
            request_id=None,
            trace_id=get_trace_id(),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    @app.get("/healthz", tags=["platform"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/readyz",
        response_model=ReadinessResponse,
        responses={503: {"model": ErrorResponse}},
        tags=["platform"],
    )
    async def readyz(request: Request) -> ReadinessResponse | JSONResponse:
        checker: DependencyChecker = request.app.state.dependency_checker
        unavailable = await checker.unavailable_dependencies()
        if unavailable:
            error = ErrorResponse(
                code="dependency_unavailable",
                message="Uma ou mais dependências não estão disponíveis.",
                details={"dependencies": unavailable},
                request_id=request.state.request_id,
                trace_id=get_trace_id(),
            )
            return JSONResponse(status_code=503, content=error.model_dump())

        return ReadinessResponse(status="ok", dependencies=checker.dependency_names)

    @app.get("/api/v1/meta", response_model=MetaResponse, tags=["platform"])
    async def meta(request: Request) -> MetaResponse:
        current_settings: Settings = request.app.state.settings
        return MetaResponse(
            version=current_settings.app_version,
            environment=current_settings.environment,
            service=current_settings.service_name,
            trace_id=get_trace_id(),
        )

    @app.get("/docs", include_in_schema=False)
    @app.get("/api/docs", include_in_schema=False)
    async def scalar_docs() -> HTMLResponse:
        return HTMLResponse(
            """<!doctype html>
<html>
  <head>
    <title>Mentora AI API - Scalar Docs</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
  </head>
  <body>
    <script id="api-reference" data-url="/openapi.json"></script>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
  </body>
</html>"""
        )

    app.include_router(identity_router)
    app.include_router(tenancy_router)
    app.include_router(documents_router)
    app.include_router(chat_router)
    app.include_router(feedback_router)
    app.include_router(classes_router)

    return app


app = create_app()
