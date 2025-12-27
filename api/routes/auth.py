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


def _set_refresh_cookie(response: Response, token: str, *, max_age_seconds: int | None = None) -> None:
    if not bool(settings.AUTH_REFRESH_COOKIE):
        return
    response.set_cookie(
        key=_refresh_cookie_name(),
        value=token,
        httponly=True,
        secure=bool(settings.COOKIE_SECURE),
        samesite=str(settings.COOKIE_SAMESITE or "Lax"),
        path="/",
        max_age=max_age_seconds,
    )


def _clear_refresh_cookie(response: Response) -> None:
    if not bool(settings.AUTH_REFRESH_COOKIE):
        return
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
    _count, over, retry_after = rate_limit.incr_and_check_detailed(ip, "auth_login")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": str(retry_after)})

    try:
        from api.auth.service import login_user

        refresh_ttl_days = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30") or 30)
        user, tokens = login_user(
            email=payload.email,
            password=payload.password,
            ip=ip,
            user_agent=request.headers.get("user-agent", ""),
            refresh_ttl_days=refresh_ttl_days,
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

    _set_refresh_cookie(response, tokens.refresh_token, max_age_seconds=refresh_ttl_days * 86400)
    body = {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "access_token": tokens.access_token,
    }
    if not bool(settings.AUTH_REFRESH_COOKIE):
        body["refresh_token"] = tokens.refresh_token
    return body


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
    _count, over, retry_after = rate_limit.incr_and_check_detailed(ip, "auth_register")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": str(retry_after)})

    try:
        from api.auth.service import register_user

        refresh_ttl_days = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30") or 30)
        user, tokens = register_user(
            email=payload.email,
            password=payload.password,
            ip=ip,
            user_agent=request.headers.get("user-agent", ""),
            refresh_ttl_days=refresh_ttl_days,
            access_ttl_minutes=int(os.getenv("JWT_EXPIRE", "15") or 15),
        )
    except ValueError as e:
        if str(e) == "email_taken":
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception:
        raise HTTPException(status_code=500, detail="Registration failed")

    _set_refresh_cookie(response, tokens.refresh_token, max_age_seconds=refresh_ttl_days * 86400)
    response.status_code = 201
    body = {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "access_token": tokens.access_token,
    }
    if not bool(settings.AUTH_REFRESH_COOKIE):
        body["refresh_token"] = tokens.refresh_token
    return body


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
    _count, over, retry_after = rate_limit.incr_and_check_detailed(ip, "forgot_password")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": str(retry_after)})

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    email = (payload or {}).get("email")

    # Add an additional limiter keyed by email hash (enumeration-safe).
    try:
        from api.security.rate_limit import incr_and_check_identifier_detailed

        normalized = str(email or "").strip().lower()
        if normalized:
            email_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            _email_count, email_over, email_retry_after = incr_and_check_identifier_detailed(email_hash, "forgot_password_email")
            if email_over:
                raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": str(email_retry_after)})
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
    if not refresh:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        refresh = (payload or {}).get("refresh_token")

    if refresh:
        try:
            from api.auth.repo import find_refresh_token, revoke_refresh_token
            from api.auth.repo import insert_audit_event
            from api.auth.tokens import hash_token

            rec = find_refresh_token(token_hash=hash_token(str(refresh)))
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
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        refresh = (payload or {}).get("refresh_token")
    if not refresh:
        raise HTTPException(status_code=401, detail="Not authenticated")

    ip = _client_ip(request)
    try:
        from api.auth.service import refresh_tokens

        refresh_ttl_days = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30") or 30)
        user, tokens = refresh_tokens(
            refresh_token=refresh,
            ip=ip,
            user_agent=request.headers.get("user-agent", ""),
            refresh_ttl_days=refresh_ttl_days,
            access_ttl_minutes=int(os.getenv("JWT_EXPIRE", "15") or 15),
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    except Exception:
        raise HTTPException(status_code=500, detail="Refresh failed")

    _set_refresh_cookie(response, tokens.refresh_token, max_age_seconds=refresh_ttl_days * 86400)
    body = {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "access_token": tokens.access_token,
    }
    if not bool(settings.AUTH_REFRESH_COOKIE):
        body["refresh_token"] = tokens.refresh_token
    return body


@router.post("/auth/oauth/google")
async def auth_oauth_google(request: Request, response: Response):
    ip = _client_ip(request)
    _count, over, retry_after = rate_limit.incr_and_check_detailed(ip, "auth_oauth_google")
    if over:
        raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": str(retry_after)})

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    id_token = (payload or {}).get("credential") or (payload or {}).get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="Invalid request")

    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    try:
        from api.services.oauth_google import verify_google_id_token

        ident = verify_google_id_token(id_token=str(id_token), audience=str(settings.GOOGLE_OAUTH_CLIENT_ID))
    except ValueError:
        raise HTTPException(status_code=401, detail="OAuth rejected")
    except Exception:
        raise HTTPException(status_code=500, detail="OAuth failed")

    try:
        from api.auth import repo
        from api.auth.tokens import create_access_token, new_refresh_token, hash_token

        # 1) If provider account already linked, sign in that user.
        linked = repo.find_oauth_account(provider="google", provider_account_id=ident.sub)
        user = None
        if linked is not None:
            user = repo.get_user_by_id(linked["user_id"])

        # 2) Else: try to attach to an existing local user by email, under merge rules.
        if user is None:
            existing = repo.get_user_by_email(ident.email)
            if existing is not None:
                # Merge/link only if local email is already verified OR Google says verified.
                if (existing.is_email_verified is True) or (ident.email_verified is True):
                    try:
                        repo.create_oauth_account(
                            user_id=existing.id,
                            provider="google",
                            provider_account_id=ident.sub,
                            email=ident.email,
                        )
                    except Exception:
                        # Ignore duplicates due to race.
                        pass
                    user = existing
                else:
                    repo.insert_audit_event(
                        user_id=existing.id,
                        action="auth.oauth_link_rejected",
                        ip=ip,
                        user_agent=request.headers.get("user-agent", ""),
                        metadata={"provider": "google"},
                    )
                    raise HTTPException(status_code=401, detail="OAuth rejected")
            else:
                # 3) Create new user and link.
                user = repo.create_user(email=ident.email, password_hash="")
                try:
                    repo.update_profile(
                        user_id=user.id,
                        display_name=(ident.name or ""),
                        avatar_url=(ident.picture or ""),
                        bio=None,
                    )
                except Exception:
                    pass
                if ident.email_verified:
                    try:
                        repo.set_user_email_verified(user_id=user.id)
                    except Exception:
                        pass
                try:
                    repo.create_oauth_account(
                        user_id=user.id,
                        provider="google",
                        provider_account_id=ident.sub,
                        email=ident.email,
                    )
                except Exception:
                    pass

        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="OAuth rejected")

        refresh_ttl_days = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30") or 30)
        refresh = new_refresh_token()
        _token_id, _expires_at = repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_token(refresh),
            ttl_days=refresh_ttl_days,
            ip=ip,
            user_agent=request.headers.get("user-agent", ""),
        )
        access = create_access_token(subject=str(user.id), email=user.email, ttl_minutes=int(os.getenv("JWT_EXPIRE", "15") or 15))

        repo.insert_audit_event(user_id=user.id, action="auth.oauth_login", ip=ip, user_agent=request.headers.get("user-agent", ""), metadata={"provider": "google"})

        _set_refresh_cookie(response, refresh, max_age_seconds=refresh_ttl_days * 86400)
        body = {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "access_token": access,
        }
        if not bool(settings.AUTH_REFRESH_COOKIE):
            body["refresh_token"] = refresh
        return body
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="OAuth failed")
