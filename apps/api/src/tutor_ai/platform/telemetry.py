"""OpenTelemetry bootstrap for the API."""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

from tutor_ai.platform.config import Settings


def configure_tracing(app: FastAPI, settings: Settings) -> None:
    """Export FastAPI spans to the configured OpenTelemetry Collector."""
    if not settings.telemetry_enabled:
        return
    if not getattr(app.state, "tracing_configured", False):
        endpoint = f"{str(settings.otel_exporter_otlp_endpoint).rstrip('/')}/v1/traces"
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: settings.service_name,
                "deployment.environment.name": settings.environment,
            }
        )
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        app.state.tracing_configured = True
