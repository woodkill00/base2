from __future__ import annotations

import os
import re
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from api.security.identity import OAuthStateError, OAuthStateSigner
from api.settings import settings

router = APIRouter()


class OAuthStartResponse(BaseModel):
    provider: str
    authorization_url: str
    state: str
    expires_in: int


class OAuthStartRequest(BaseModel):
    return_path: str = '/'


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


def _project_slug() -> str:
    raw = (os.getenv('PROJECT_NAME') or os.getenv('COMPOSE_PROJECT_NAME') or 'base2').lower()
    return re.sub(r'[^a-z0-9_-]+', '-', raw).strip('-_') or 'base2'


def _state_cookie_name() -> str:
    return f'{_project_slug()}_oauth_state'


def _require_google_provider() -> OAuthStateSigner:
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(status_code=404, detail='oauth_provider_disabled')
    if not all(
        (
            settings.GOOGLE_OAUTH_CLIENT_ID,
            settings.GOOGLE_OAUTH_CLIENT_SECRET,
            settings.GOOGLE_OAUTH_REDIRECT_URI,
            settings.OAUTH_STATE_SECRET,
        )
    ):
        raise HTTPException(status_code=503, detail='oauth_provider_unavailable')
    try:
        return OAuthStateSigner(secret=str(settings.OAUTH_STATE_SECRET))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail='oauth_provider_unavailable') from exc


@router.post('/oauth/google/start', response_model=OAuthStartResponse)
async def oauth_google_start(payload: OAuthStartRequest, response: Response) -> OAuthStartResponse:
    signer = _require_google_provider()
    try:
        issued = signer.issue(return_path=payload.return_path)
    except OAuthStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    query = urlencode(
        {
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': issued.state,
            'nonce': issued.nonce,
            'access_type': 'offline',
            'prompt': 'select_account',
        }
    )
    response.set_cookie(
        key=_state_cookie_name(),
        value=issued.browser_binding,
        max_age=issued.expires_in,
        httponly=True,
        secure=bool(settings.COOKIE_SECURE),
        samesite='Lax',
        path='/api/oauth/google/callback',
    )
    return OAuthStartResponse(
        provider='google',
        authorization_url=f'https://accounts.google.com/o/oauth2/v2/auth?{query}',
        state=issued.state,
        expires_in=issued.expires_in,
    )


@router.post('/oauth/google/callback')
async def oauth_google_callback(
    payload: OAuthCallbackRequest, request: Request, response: Response
):
    signer = _require_google_provider()
    binding = request.cookies.get(_state_cookie_name(), '')
    response.delete_cookie(_state_cookie_name(), path='/api/oauth/google/callback')
    if not binding:
        raise HTTPException(status_code=401, detail='oauth_state_missing')
    try:
        state = signer.verify(payload.state, browser_binding=binding)
        from api.services.oauth_google import (
            exchange_google_authorization_code,
            verify_google_id_token,
        )

        id_token = await exchange_google_authorization_code(
            code=payload.code,
            client_id=str(settings.GOOGLE_OAUTH_CLIENT_ID),
            client_secret=str(settings.GOOGLE_OAUTH_CLIENT_SECRET),
            redirect_uri=str(settings.GOOGLE_OAUTH_REDIRECT_URI),
        )
        ident = verify_google_id_token(
            id_token=id_token,
            audience=str(settings.GOOGLE_OAUTH_CLIENT_ID),
            expected_nonce=str(state['nonce']),
        )
        from api.routes.auth import complete_google_oauth_identity

        result = await complete_google_oauth_identity(
            ident=ident, request=request, response=response
        )
        result['return_path'] = state['return_path']
        return result
    except OAuthStateError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail='oauth_rejected') from exc
