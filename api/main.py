from fastapi import FastAPI, HTTPException
import os
import httpx

ENV = os.getenv("ENV", "development")
DJANGO_SERVICE_URL = os.getenv("DJANGO_SERVICE_URL", "http://django:8001")

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
async def get_me():
    # Example proxy call to Django internal route
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{DJANGO_SERVICE_URL}/internal/users/me")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))
