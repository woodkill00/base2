# Observability

## OpenTelemetry (FastAPI)

The API supports optional OpenTelemetry tracing.

- Enable: set `OTEL_ENABLED=true`
- Service name: `OTEL_SERVICE_NAME=base2-api`
- Exporter:
  - If `OTEL_EXPORTER_OTLP_ENDPOINT` is set, traces are exported via OTLP/HTTP.
  - Otherwise, traces are exported to console (dev-friendly).

Trace headers should be forwarded end-to-end by the edge proxy (Traefik) and upstream services.

## Golden Signals Checklist

Track these signals for the API and edge:

- **Traffic**: request rate by endpoint (e.g. `/api/auth/login`, `/api/auth/refresh`)
- **Errors**: 4xx/5xx rate, auth failures vs server errors
- **Latency**: p50/p95/p99 for key endpoints
- **Saturation**: CPU/memory, DB connection pool pressure, Redis availability

## Suggested Targets (informal)

- Auth endpoints p95 latency: < 300ms (steady-state)
- Error rate (5xx): < 0.5%

## Runbooks (minimum)

- **Auth failures spike**: check rate limiting, lockouts, upstream availability
- **Refresh failures**: validate cookie mode vs header mode, token rotation behavior
- **DB errors**: check migrations applied, connection settings, statement timeouts
