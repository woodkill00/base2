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
