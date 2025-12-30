from fastapi import FastAPI, HTTPException, Body, Request
import logging
import os
import time
from celery.result import AsyncResult
from api import tasks  # ensure tasks module is importable
from api.db import db_ping
from fastapi.middleware.cors import CORSMiddleware

from api.logging import configure_logging
from typing import Any

_metrics: Any
try:
    from api.metrics import metrics as _metrics
except Exception:  # pragma: no cover
    _metrics = None

metrics: Any = _metrics


try:
    from api.settings import settings
except Exception as e:
    # Loud startups: in non-development, fail fast and log clearly.
    env_val = (os.getenv("ENV", "development") or "").strip().lower()
    try:
        configure_logging(service="api")
    except Exception:
        pass
    _boot_logger = logging.getLogger("api.boot")
    _boot_logger.error("settings_import_failed", extra={"env": env_val, "error": str(e)})
    if env_val in {"staging", "production"}:
        raise
    # Development fallback only
    class _Fallback:
        ENV = os.getenv("ENV", "development")
        API_DOCS_ENABLED = (os.getenv("API_DOCS_ENABLED", "") or "").strip().lower() in {"1", "true", "yes", "on"} or (ENV.strip().lower() != "production")
        API_DOCS_URL = os.getenv("API_DOCS_URL", "/docs") or "/docs"
        API_REDOC_URL = os.getenv("API_REDOC_URL", "/redoc") or "/redoc"
        API_OPENAPI_URL = os.getenv("API_OPENAPI_URL", "/openapi.json") or "/openapi.json"
        FRONTEND_URL = os.getenv("FRONTEND_URL", "") or ""
        E2E_TEST_MODE = (os.getenv("E2E_TEST_MODE", "") or "").strip().lower() in {"1", "true", "yes", "on"}

    settings = _Fallback()

_docs_enabled = bool(getattr(settings, "API_DOCS_ENABLED", True))
_docs_url = str(getattr(settings, "API_DOCS_URL", "/docs"))
_redoc_url = str(getattr(settings, "API_REDOC_URL", "/redoc"))
_openapi_url = str(getattr(settings, "API_OPENAPI_URL", "/openapi.json"))

_E2E_TEST_MODE = bool(getattr(settings, "E2E_TEST_MODE", False))

configure_logging(service="api")
logger = logging.getLogger("api.http")

app = FastAPI(
    title="Base2 API",
    docs_url=(_docs_url if _docs_enabled else None),
    redoc_url=(_redoc_url if _docs_enabled else None),
    openapi_url=(_openapi_url if _docs_enabled else None),
)

# Observability: optional OpenTelemetry
try:
    from api.otel import configure_otel

    configure_otel(app)
except Exception:
    pass

# CORS (strict allowlist; required for browser credentialed requests)
try:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    origins = [o.strip() for o in raw.split(",") if o.strip()] if raw else []

    if not origins:
        # Dev-friendly defaults.
        origins = [
            "http://localhost",
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
        ]
        try:
            if getattr(settings, "FRONTEND_URL", ""):
                origins.append(str(getattr(settings, "FRONTEND_URL", "")).rstrip("/"))
        except Exception:
            pass

    allow_credentials = True
    if "*" in origins:
        # Disallow wildcard origins with credentials.
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Requested-With"],
    )
except Exception:
    pass

# Ensure DB schema is present (idempotent migrations)
try:
    from api.migrations.runner import apply_migrations

    apply_migrations()
except Exception:
    # Keep boot resilient; schema creation will be retried on next boot.
    pass

# Middleware: request id
try:
    from api.middleware.request_id import request_id_middleware

    @app.middleware("http")
    async def _add_request_id(request: Request, call_next):
        return await request_id_middleware(request, call_next)
except Exception:
    pass

# Middleware: tenant context
try:
    from api.middleware.tenant import tenant_context_middleware

    @app.middleware("http")
    async def _add_tenant_context(request: Request, call_next):
        return await tenant_context_middleware(request, call_next)
except Exception:
    pass


@app.middleware("http")
async def _access_log(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = int((time.perf_counter() - start) * 1000)
        req_id = getattr(request.state, "request_id", "")
        try:
            if metrics is not None:
                metrics.observe(status=500, latency_ms=latency_ms)
        except Exception:
            pass
        logger.exception(
            "request_failed",
            extra={
                "request_id": req_id,
                "method": request.method,
                "path": request.url.path,
                "status": 500,
                "latency_ms": latency_ms,
                "client_ip": (request.client.host if request.client else "unknown"),
                "user_agent": request.headers.get("user-agent", ""),
            },
        )
        raise

    latency_ms = int((time.perf_counter() - start) * 1000)
    req_id = getattr(request.state, "request_id", "")
    try:
        if metrics is not None:
            metrics.observe(status=int(getattr(response, "status_code", 0) or 0), latency_ms=latency_ms)
    except Exception:
        pass
    logger.info(
        "request",
        extra={
            "request_id": req_id,
            "method": request.method,
            "path": request.url.path,
            "status": int(getattr(response, "status_code", 0) or 0),
            "latency_ms": latency_ms,
            "client_ip": (request.client.host if request.client else "unknown"),
            "user_agent": request.headers.get("user-agent", ""),
        },
    )
    return response

# Error handlers: ensure consistent {detail}
try:
    from api.middleware.errors import register_error_handlers

    register_error_handlers(app)
except Exception:
    pass

# Customize OpenAPI to include required security schemes from the external contract.
try:
    from fastapi.openapi.utils import get_openapi

    def custom_openapi():
        openapi_schema = get_openapi(
            title=app.title,
            version="0.1.0",
            description="External API contract surface for Base2",
            routes=app.routes,
        )
        comps = openapi_schema.setdefault("components", {})
        sec = comps.setdefault("securitySchemes", {})
        # Session cookie scheme required by contract
        sec["SessionCookie"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": "base2_session",
            "description": "HttpOnly cookie carrying the primary session credential.",
        }
        # CSRF token header scheme required by contract
        sec["CsrfToken"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-CSRF-Token",
            "description": "CSRF token header required for state-changing requests.",
        }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    # Assign override and eagerly generate schema so it's ready before first request
    app.openapi = custom_openapi
    try:
        app.openapi()
    except Exception:
        pass
except Exception:
    # If OpenAPI customization fails, proceed without breaking runtime.
    pass


# External routes (proxy to Django internal)
try:
    from api.routes.auth import router as auth_router
    from api.routes.metrics import router as metrics_router
    from api.routes.oauth import router as oauth_router
    from api.routes.users import router as users_router
    from api.routes.tenant import router as tenant_router
    from api.routes.privacy import router as privacy_router

    app.include_router(auth_router)
    app.include_router(metrics_router)
    app.include_router(oauth_router)
    app.include_router(users_router)
    app.include_router(tenant_router)
    app.include_router(privacy_router)

    # E2E-only helpers (must be explicitly enabled; never in production).
    if _E2E_TEST_MODE and str(getattr(settings, "ENV", "development")).strip().lower() != "production":
        try:
            from api.routes.test_support import router as test_support_router

            app.include_router(test_support_router)
        except Exception:
            pass
except Exception:
    # Keep app bootable even if routes fail to import.
    pass

@app.get("/health")
async def health():
    return {"ok": True, "service": "api", "db_ok": db_ping()}


@app.get("/flags")
async def flags():
    try:
        from api.flags import get_flags

        return {"flags": get_flags()}
    except Exception:
        return {"flags": {}}


# --- Catalog (proxy to Django internal) ---
@app.get("/items")
async def list_items():
    raise HTTPException(status_code=501, detail="/api/items is not implemented yet")


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    raise HTTPException(status_code=501, detail="/api/items/{item_id} is not implemented yet")


@app.post("/items")
async def create_item(payload: dict = Body(...)):
    raise HTTPException(status_code=501, detail="/api/items POST is not implemented yet")


# --- Celery helper endpoints (optional) ---
async def _enqueue_celery_ping(request: Request):
    try:
        rid = getattr(request.state, "request_id", None) or request.headers.get("x-request-id")
        res = tasks.ping.delay(request_id=(str(rid) if rid else None))
        return {"task_id": res.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/celery/ping")
async def celery_ping_root(request: Request):
    return await _enqueue_celery_ping(request)


async def _read_celery_result(task_id: str):
    try:
        ar = AsyncResult(task_id, app=tasks.app)
        return {
            "task_id": task_id,
            "ready": ar.ready(),
            "successful": ar.successful() if ar.ready() else False,
            "state": ar.state,
            "result": (ar.result if ar.ready() else None),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"result_failed: {e}")


@app.get("/celery/result/{task_id}")
async def celery_result_root(task_id: str):
    return await _read_celery_result(task_id)
