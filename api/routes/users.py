from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.routes.auth import _client_ip

router = APIRouter()


def _require_user_id(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        from api.auth.tokens import decode_access_token
        from uuid import UUID

        payload = decode_access_token(token)
        return UUID(str(payload.get("sub")))
    except Exception:
        raise HTTPException(status_code=401, detail="Not authenticated")


class _PatchMeRequest(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    email: str | None = None


@router.get("/users/me")
async def users_me(request: Request):
    user_id = _require_user_id(request)
    try:
        from api.auth.repo import get_user_by_id

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
        raise HTTPException(status_code=400, detail="Invalid request")


@router.patch("/users/me")
async def users_me_patch(request: Request, payload: _PatchMeRequest):
    user_id = _require_user_id(request)

    try:
        from api.auth import repo
        from api.auth.service import issue_verify_email

        # Email change (optional)
        new_email = (payload.email or "").strip().lower() if payload.email is not None else None
        if new_email is not None:
            if not new_email:
                raise HTTPException(status_code=422, detail=[{"loc": ["body", "email"], "msg": "Email is required", "type": "value_error"}])
            try:
                repo.update_user_email(user_id=user_id, email=new_email)
                try:
                    issue_verify_email(
                        email=new_email,
                        host=request.headers.get("host"),
                        proto=request.headers.get("x-forwarded-proto"),
                        request_id=request.headers.get("x-request-id"),
                    )
                except Exception:
                    pass
                try:
                    repo.insert_audit_event(
                        user_id=user_id,
                        action="user.email_change_requested",
                        ip=_client_ip(request),
                        user_agent=request.headers.get("user-agent", ""),
                    )
                except Exception:
                    pass
            except ValueError as e:
                if str(e) == "email_taken":
                    raise HTTPException(status_code=422, detail=[{"loc": ["body", "email"], "msg": "Email already registered", "type": "value_error"}])
                raise

        user = repo.update_profile(
            user_id=user_id,
            display_name=payload.display_name,
            avatar_url=payload.avatar_url,
            bio=payload.bio,
        )

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
        raise HTTPException(status_code=400, detail="Invalid request")
