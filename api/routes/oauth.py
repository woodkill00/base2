from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ._proxy import proxy_json


router = APIRouter()


@router.post("/oauth/google/start")
async def oauth_google_start(request: Request, response: Response):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/oauth/google/start",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/oauth/google/callback")
async def oauth_google_callback(request: Request, response: Response):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/oauth/google/callback",
        json_body=payload,
        forward_csrf=False,
    )
