from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request


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
