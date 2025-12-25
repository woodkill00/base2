from __future__ import annotations

from fastapi import APIRouter, Request, Response

from api.settings import settings

from ._proxy import proxy_json, require_session_cookie


router = APIRouter()


@router.get("/users/me")
async def users_me(request: Request, response: Response):
    require_session_cookie(request, settings.SESSION_COOKIE_NAME)
    return await proxy_json(
        request=request,
        response=response,
        method="GET",
        upstream_path="/internal/api/users/me",
        json_body=None,
        forward_csrf=False,
    )


@router.patch("/users/me")
async def users_me_patch(request: Request, response: Response):
    require_session_cookie(request, settings.SESSION_COOKIE_NAME)
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    allowed_keys = {"display_name", "avatar_url", "bio"}
    filtered_payload = {k: v for k, v in (payload or {}).items() if k in allowed_keys}
    return await proxy_json(
        request=request,
        response=response,
        method="PATCH",
        upstream_path="/internal/api/users/me",
        json_body=filtered_payload,
        forward_csrf=True,
    )
