from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class PublicPrincipal:
    user_id: UUID
    authenticated_at: datetime
    recently_authenticated: bool


def require_authenticated_principal(request: Request) -> PublicPrincipal:
    authorization = request.headers.get('authorization', '')
    if not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='not_authenticated')
    token = authorization.split(' ', 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail='not_authenticated')
    try:
        from api.auth.tokens import decode_access_token

        payload = decode_access_token(token)
        user_id = UUID(str(payload.get('sub')))
        issued_at = datetime.fromtimestamp(int(payload.get('iat')), tz=timezone.utc)
        return PublicPrincipal(
            user_id=user_id,
            authenticated_at=issued_at,
            recently_authenticated=payload.get('reauth') is True,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail='not_authenticated') from exc


def require_authenticated_user(request: Request) -> UUID:
    authorization = request.headers.get('authorization', '')
    if not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='not_authenticated')
    token = authorization.split(' ', 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail='not_authenticated')
    try:
        from api.auth.tokens import decode_access_token

        payload = decode_access_token(token)
        return UUID(str(payload.get('sub')))
    except Exception as exc:
        raise HTTPException(status_code=401, detail='not_authenticated') from exc
