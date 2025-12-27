from __future__ import annotations

import os
import hashlib

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from api.security import rate_limit
from api.settings import settings

from ._proxy import _client_ip, proxy_json, require_session_cookie


router = APIRouter()


class _LoginRequest(BaseModel):
    email: str
    password: str


class _RegisterRequest(BaseModel):
    email: str
    password: str


def _refresh_cookie_name() -> str:
    return "base2_refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_refresh_cookie_name(),
        value=token,
        httponly=True,
        secure=bool(settings.COOKIE_SECURE),
        samesite=str(settings.COOKIE_SAMESITE or "Lax"),
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_refresh_cookie_name(),
        path="/",
    )


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
async def auth_login(request: Request, response: Response, payload: _LoginRequest):
    ip = _client_ip(request)
    _count, over = rate_limit.incr_and_check(ip, "auth_login")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited")

    try:
        from api.auth.service import login_user

        user, tokens = login_user(
            email=payload.email,
            password=payload.password,
            ip=ip,
            user_agent=request.headers.get("user-agent", ""),
            refresh_ttl_days=int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30") or 30),
            access_ttl_minutes=int(os.getenv("JWT_EXPIRE", "15") or 15),
        )
    except ValueError as e:
        if str(e) == "invalid_credentials":
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if str(e) == "inactive":
            raise HTTPException(status_code=403, detail="Account inactive")
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception:
        raise HTTPException(status_code=500, detail="Login failed")

    _set_refresh_cookie(response, tokens.refresh_token)
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "access_token": tokens.access_token,
    }


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
async def auth_register(request: Request, response: Response, payload: _RegisterRequest):
    ip = _client_ip(request)
    _count, over = rate_limit.incr_and_check(ip, "auth_register")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited")

    try:
        from api.auth.service import register_user

        user, tokens = register_user(
            email=payload.email,
            password=payload.password,
            ip=ip,
            user_agent=request.headers.get("user-agent", ""),
            refresh_ttl_days=int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30") or 30),
            access_ttl_minutes=int(os.getenv("JWT_EXPIRE", "15") or 15),
        )
    except ValueError as e:
        if str(e) == "email_taken":
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception:
        raise HTTPException(status_code=500, detail="Registration failed")

    _set_refresh_cookie(response, tokens.refresh_token)
    response.status_code = 201
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "access_token": tokens.access_token,
    }


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
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    token = (payload or {}).get("token")
    try:
        from api.auth.service import verify_email
        from api.auth.repo import insert_audit_event

        verify_email(token=str(token or ""))
        try:
            insert_audit_event(
                user_id=None,
                action="user.verify_email",
                ip=_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
            )
        except Exception:
            pass
        return {"detail": "Email verified"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    except Exception:
        raise HTTPException(status_code=500, detail="Verification failed")


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
        raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": "900"})

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    email = (payload or {}).get("email")

    # Add an additional limiter keyed by email hash (enumeration-safe).
    try:
        from api.security.rate_limit import incr_and_check_identifier

        normalized = str(email or "").strip().lower()
        if normalized:
            email_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            email_count, _ = incr_and_check_identifier(email_hash, "forgot_password_email")
            if email_count > 5:
                raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": "900"})
    except HTTPException:
        raise
    except Exception:
        # Never break forgot-password because of limiter errors.
        pass

    try:
        from api.auth.service import issue_password_reset
        from api.auth.repo import insert_audit_event

        issue_password_reset(
            email=str(email or "").strip(),
            host=request.headers.get("host"),
            proto=request.headers.get("x-forwarded-proto"),
            request_id=request.headers.get("x-request-id"),
        )
        try:
            insert_audit_event(
                user_id=None,
                action="user.reset_password_requested",
                ip=ip,
                user_agent=request.headers.get("user-agent", ""),
            )
        except Exception:
            pass
    except Exception:
        # Enumeration-safe: never leak existence, never error.
        pass

    return {"detail": "If the account exists, a password reset email has been sent"}


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
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    token = (payload or {}).get("token")
    password = (payload or {}).get("password")

    try:
        from api.auth.service import reset_password
        from api.auth.repo import insert_audit_event

        reset_password(token=str(token or ""), new_password=str(password or ""))
        try:
            insert_audit_event(
                user_id=None,
                action="user.reset_password",
                ip=_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
            )
        except Exception:
            pass
        return {"detail": "Password reset"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request or token")
    except Exception:
        raise HTTPException(status_code=500, detail="Reset failed")


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
    refresh = request.cookies.get(_refresh_cookie_name())
    if refresh:
        try:
            from api.auth.repo import find_refresh_token, revoke_refresh_token
            from api.auth.repo import insert_audit_event
            from api.auth.tokens import hash_token

            rec = find_refresh_token(token_hash=hash_token(refresh))
            if rec is not None:
                revoke_refresh_token(token_id=rec["id"], replaced_by_token_id=None)
                insert_audit_event(
                    user_id=rec.get("user_id"),
                    action="auth.logout",
                    ip=_client_ip(request),
                    user_agent=request.headers.get("user-agent", ""),
                )
        except Exception:
            pass

    _clear_refresh_cookie(response)
    response.status_code = 204
    return None


@router.get("/auth/me")
async def auth_me(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        from api.auth.repo import get_user_by_id
        from api.auth.tokens import decode_access_token
        from uuid import UUID

        payload = decode_access_token(token)
        user_id = UUID(str(payload.get("sub")))
        user = get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Not authenticated")


@router.patch("/auth/me")
async def auth_me_patch(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        body = await request.json()
    except Exception:
        body = {}

    allowed_keys = {"display_name", "avatar_url", "bio"}
    filtered = {k: v for k, v in (body or {}).items() if k in allowed_keys}

    try:
        from api.auth.repo import update_profile
        from api.auth.tokens import decode_access_token
        from uuid import UUID

        payload = decode_access_token(token)
        user_id = UUID(str(payload.get("sub")))
        user = update_profile(
            user_id=user_id,
            display_name=filtered.get("display_name"),
            avatar_url=filtered.get("avatar_url"),
            bio=filtered.get("bio"),
        )
        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
        }
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")


@router.post("/auth/refresh")
async def auth_refresh(request: Request, response: Response):
    refresh = request.cookies.get(_refresh_cookie_name())
    if not refresh:
        raise HTTPException(status_code=401, detail="Not authenticated")

    ip = _client_ip(request)
    try:
        from api.auth.service import refresh_tokens

        user, tokens = refresh_tokens(
            refresh_token=refresh,
            ip=ip,
            user_agent=request.headers.get("user-agent", ""),
            refresh_ttl_days=int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30") or 30),
            access_ttl_minutes=int(os.getenv("JWT_EXPIRE", "15") or 15),
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    except Exception:
        raise HTTPException(status_code=500, detail="Refresh failed")

    _set_refresh_cookie(response, tokens.refresh_token)
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "access_token": tokens.access_token,
    }


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
