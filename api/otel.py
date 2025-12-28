from __future__ import annotations

import os


def configure_otel(app) -> None:
    """Best-effort OpenTelemetry wiring.

    This is intentionally optional: if OTEL deps aren't installed or OTEL isn't enabled,
    the app should still run.
    """

    enabled = os.getenv("OTEL_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        service_name = os.getenv("OTEL_SERVICE_NAME", "base2-api")
        resource = Resource.create({"service.name": service_name})

        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        if endpoint:
            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        else:
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

        try:
            from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

            Psycopg2Instrumentor().instrument()
        except Exception:
            pass

        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        # Never break runtime because tracing couldn't be enabled.
        return
