from fastapi import FastAPI, HTTPException, Body, Request, Response
import os
from pydantic import BaseModel
from celery.result import AsyncResult
import tasks  # ensure tasks module is importable
from db import db_ping


class LoginPayload(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str


ENV = os.getenv("ENV", "development")


def _session_cookie_name() -> str:
    return os.getenv("SESSION_COOKIE_NAME", "base2_session")


def _has_session_cookie(request: Request) -> bool:
    try:
        return bool(request.cookies.get(_session_cookie_name()))
    except Exception:
        return False

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

@app.get("/health")
async def health():
    return {"ok": True, "service": "api", "db_ok": db_ping()}

@app.get("/users/me")
async def get_me(request: Request):
    if not _has_session_cookie(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Django-backed implementation has been removed; FastAPI is now decoupled.
    raise HTTPException(status_code=501, detail="/api/users/me is not implemented yet")
# --- Users (proxy to Django internal) ---
@app.get("/users")
async def list_users():
    raise HTTPException(status_code=501, detail="/api/users is not implemented yet")


@app.post("/users/login")
async def users_login(request: Request):
    raw = await request.body()
    # DEBUG: write raw body and headers to file immediately
    try:
        with open("/tmp/login_debug.txt", "a") as f:
            f.write("\n==== LOGIN ATTEMPT ====" + os.linesep)
            f.write("headers: " + str(dict(request.headers)) + os.linesep)
            f.write("raw body: " + repr(raw) + os.linesep)
    except Exception as e:
        pass
    try:
        payload = LoginPayload.parse_raw(raw)
    except Exception as e:
        try:
            with open("/tmp/login_debug.txt", "a") as f:
                f.write("parse error: " + str(e) + os.linesep)
        except Exception:
            pass
        raise HTTPException(status_code=422, detail=f"JSON decode error: {e}")
    # Accept either username or email, and always forward both if present
    proxy_payload = {}
    if payload.username:
        proxy_payload["username"] = payload.username
    if payload.email:
        proxy_payload["email"] = payload.email
    proxy_payload["password"] = payload.password
    if not proxy_payload.get("username") and not proxy_payload.get("email"):
        raise HTTPException(status_code=400, detail="Missing username or email")
    # Authentication is no longer proxied to Django; this will be
    # reimplemented to use FastAPI's own data models.
    raise HTTPException(status_code=501, detail="/api/users/login is not implemented yet")


@app.post("/users/signup")
async def users_signup(request: Request):
    raise HTTPException(status_code=501, detail="/api/users/signup is not implemented yet")


@app.post("/users/logout")
async def users_logout(request: Request):
    if not _has_session_cookie(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    raise HTTPException(status_code=501, detail="/api/users/logout is not implemented yet")


@app.post("/oauth/google/start")
async def oauth_google_start():
    raise HTTPException(status_code=501, detail="/api/oauth/google/start is not implemented yet")


@app.post("/oauth/google/callback")
async def oauth_google_callback():
    raise HTTPException(status_code=501, detail="/api/oauth/google/callback is not implemented yet")


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
