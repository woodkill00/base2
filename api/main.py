from fastapi import FastAPI, HTTPException, Body, Request
import logging
import os
import time
from celery.result import AsyncResult
from api import tasks  # ensure tasks module is importable
from api.db import db_ping

from api.logging import configure_logging


ENV = os.getenv("ENV", "development")

configure_logging(service="api")
logger = logging.getLogger("api.http")

app = FastAPI(
    title="Base2 API",
    docs_url=None if ENV == "production" else "/docs",
    redoc_url=None if ENV == "production" else "/redoc",
    openapi_url=None if ENV == "production" else "/openapi.json",
)

# Middleware: request id
try:
    from api.middleware.request_id import request_id_middleware

    @app.middleware("http")
    async def _add_request_id(request: Request, call_next):
        return await request_id_middleware(request, call_next)
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
    from api.routes.oauth import router as oauth_router
    from api.routes.users import router as users_router

    app.include_router(auth_router)
    app.include_router(oauth_router)
    app.include_router(users_router)
except Exception:
    # Keep app bootable even if routes fail to import.
    pass

@app.get("/health")
async def health():
    return {"ok": True, "service": "api", "db_ok": db_ping()}


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
async def _enqueue_celery_ping():
    try:
        res = tasks.ping.delay()
        return {"task_id": res.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/celery/ping")
async def celery_ping_root():
    return await _enqueue_celery_ping()


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
