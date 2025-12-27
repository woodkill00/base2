from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from api.security import rate_limit
from api.settings import settings

from ._proxy import _client_ip, proxy_json, require_session_cookie


router = APIRouter()


@router.post("/users/login")
async def users_login(request: Request, response: Response):
    ip = _client_ip(request)
    _count, over = rate_limit.incr_and_check(ip, "login")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited")

    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/login",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/auth/login")
async def auth_login(request: Request, response: Response):
    ip = _client_ip(request)
    _count, over = rate_limit.incr_and_check(ip, "login")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited")

    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/login",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/users/signup")
async def users_signup(request: Request, response: Response):
    ip = _client_ip(request)
    _count, over = rate_limit.incr_and_check(ip, "signup")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited")

    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/signup",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/auth/register")
async def auth_register(request: Request, response: Response):
    ip = _client_ip(request)
    _count, over = rate_limit.incr_and_check(ip, "signup")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited")

    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/signup",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/users/verify-email")
async def users_verify_email(request: Request, response: Response):
    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/verify-email",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/auth/verify-email")
async def auth_verify_email(request: Request, response: Response):
    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/verify-email",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/users/forgot-password")
async def users_forgot_password(request: Request, response: Response):
    ip = _client_ip(request)
    count, _over = rate_limit.incr_and_check(ip, "forgot_password")
    # Heavier limit than login/signup; keep conservative by default.
    if count > 10:
        raise HTTPException(status_code=429, detail="Rate limited")

    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/forgot-password",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/auth/forgot-password")
async def auth_forgot_password(request: Request, response: Response):
    ip = _client_ip(request)
    count, _over = rate_limit.incr_and_check(ip, "forgot_password")
    if count > 10:
        raise HTTPException(status_code=429, detail="Rate limited")

    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/forgot-password",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/users/reset-password")
async def users_reset_password(request: Request, response: Response):
    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/reset-password",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/auth/reset-password")
async def auth_reset_password(request: Request, response: Response):
    payload = await request.json()
    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/reset-password",
        json_body=payload,
        forward_csrf=False,
    )


@router.post("/users/logout")
async def users_logout(request: Request, response: Response):
    require_session_cookie(request, settings.SESSION_COOKIE_NAME)

    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/logout",
        json_body=None,
        forward_csrf=True,
    )


@router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    require_session_cookie(request, settings.SESSION_COOKIE_NAME)

    return await proxy_json(
        request=request,
        response=response,
        method="POST",
        upstream_path="/internal/api/users/logout",
        json_body=None,
        forward_csrf=True,
    )


@router.get("/auth/me")
async def auth_me(request: Request, response: Response):
    require_session_cookie(request, settings.SESSION_COOKIE_NAME)
    return await proxy_json(
        request=request,
        response=response,
        method="GET",
        upstream_path="/internal/api/users/me",
        json_body=None,
        forward_csrf=False,
    )


@router.patch("/auth/me")
async def auth_me_patch(request: Request, response: Response):
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


@router.post("/auth/refresh")
async def auth_refresh():
    raise HTTPException(status_code=501, detail="/api/auth/refresh is not implemented yet")


@router.post("/auth/oauth/google")
async def auth_oauth_google(request: Request, response: Response):
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
