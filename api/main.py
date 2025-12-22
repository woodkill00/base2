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

app = FastAPI(
    title="Base2 API",
    docs_url=None if ENV == "production" else "/docs",
    redoc_url=None if ENV == "production" else "/redoc",
    openapi_url=None if ENV == "production" else "/openapi.json",
)

@app.get("/health")
async def health():
    return {"ok": True, "service": "api", "db_ok": db_ping()}

@app.get("/api/health")
async def api_health():
    return {"ok": True, "service": "api"}

@app.get("/api/users/me")
async def get_me(request: Request):
    # Django-backed implementation has been removed; FastAPI is now decoupled.
    raise HTTPException(status_code=501, detail="/api/users/me is not implemented yet")
# --- Users (proxy to Django internal) ---
@app.get("/api/users")
async def list_users():
    raise HTTPException(status_code=501, detail="/api/users is not implemented yet")


@app.post("/api/users/login")
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


@app.post("/api/users/logout")
async def users_logout(request: Request):
    raise HTTPException(status_code=501, detail="/api/users/logout is not implemented yet")


# --- Catalog (proxy to Django internal) ---
@app.get("/api/items")
async def list_items():
    raise HTTPException(status_code=501, detail="/api/items is not implemented yet")


@app.get("/api/items/{item_id}")
async def get_item(item_id: int):
    raise HTTPException(status_code=501, detail="/api/items/{item_id} is not implemented yet")


@app.post("/api/items")
async def create_item(payload: dict = Body(...)):
    raise HTTPException(status_code=501, detail="/api/items POST is not implemented yet")


# --- Celery helper endpoints (optional) ---
@app.post("/api/celery/ping")
async def celery_ping():
    try:
        res = tasks.ping.delay()
        return {"task_id": res.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.get("/api/celery/result/{task_id}")
async def celery_result(task_id: str):
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
