from fastapi import FastAPI, HTTPException, Body, Request, Response
import sys
import os
from pydantic import BaseModel
class LoginPayload(BaseModel):
    username: str = None
    email: str = None
    password: str
from typing import Optional
import os
import httpx
from celery.result import AsyncResult
import tasks  # ensure tasks module is importable

ENV = os.getenv("ENV", "development")
DJANGO_SERVICE_URL = os.getenv("DJANGO_SERVICE_URL", "http://django:8000")
DJANGO_PUBLIC_HOST = os.getenv("WEBSITE_DOMAIN", "woodkilldev.com")

app = FastAPI(
    title="Base2 API",
    docs_url=None if ENV == "production" else "/docs",
    redoc_url=None if ENV == "production" else "/redoc",
    openapi_url=None if ENV == "production" else "/openapi.json",
)

@app.get("/health")
async def health():
    return {"ok": True, "service": "api"}

@app.get("/api/health")
async def api_health():
    return {"ok": True, "service": "api"}

@app.get("/api/users/me")
async def get_me(request: Request):
    # Example proxy call to Django internal route
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{DJANGO_SERVICE_URL}/internal/users/me",
                headers={
                    "Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Proto": "https",
                    "Cookie": request.headers.get("cookie", ""),
                },
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))
# --- Users (proxy to Django internal) ---
@app.get("/api/users")
async def list_users():
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{DJANGO_SERVICE_URL}/internal/users/",
                headers={
                    "Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Proto": "https",
                },
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


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
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.post(
                f"{DJANGO_SERVICE_URL}/internal/users/login/",
                json=proxy_payload,
                headers={
                    "Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Proto": "https",
                },
            )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        # Propagate Django Set-Cookie headers to client
        response = Response(content=resp.content, media_type="application/json", status_code=resp.status_code)
        try:
            for c in resp.headers.get_list("set-cookie"):
                response.headers.append("set-cookie", c)
        except Exception:
            sc = resp.headers.get("set-cookie")
            if sc:
                response.headers.append("set-cookie", sc)
        return response
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/users/logout")
async def users_logout(request: Request):
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.post(
                f"{DJANGO_SERVICE_URL}/internal/users/logout/",
                headers={
                    "Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Proto": "https",
                    "Cookie": request.headers.get("cookie", ""),
                },
            )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        # Propagate cookie clearing if any
        response = Response(content=resp.content, media_type="application/json", status_code=resp.status_code)
        try:
            for c in resp.headers.get_list("set-cookie"):
                response.headers.append("set-cookie", c)
        except Exception:
            sc = resp.headers.get("set-cookie")
            if sc:
                response.headers.append("set-cookie", sc)
        return response
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


# --- Catalog (proxy to Django internal) ---
@app.get("/api/items")
async def list_items():
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{DJANGO_SERVICE_URL}/internal/catalog/items/",
                headers={
                    "Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Proto": "https",
                },
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/items/{item_id}")
async def get_item(item_id: int):
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{DJANGO_SERVICE_URL}/internal/catalog/items/{item_id}/",
                headers={
                    "Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Proto": "https",
                },
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/items")
async def create_item(payload: dict = Body(...)):
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.post(
                f"{DJANGO_SERVICE_URL}/internal/catalog/items/create/",
                json=payload,
                headers={
                    "Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Host": DJANGO_PUBLIC_HOST,
                    "X-Forwarded-Proto": "https",
                },
            )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


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
