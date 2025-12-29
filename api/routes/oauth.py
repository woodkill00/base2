from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class OAuthStartResponse(BaseModel):
    authorization_url: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


@router.post("/oauth/google/start", response_model=OAuthStartResponse)
async def oauth_google_start() -> OAuthStartResponse:
    raise HTTPException(status_code=501, detail="OAuth start is not implemented")


@router.post("/oauth/google/callback")
async def oauth_google_callback(_payload: OAuthCallbackRequest):
    raise HTTPException(status_code=501, detail="OAuth callback is not implemented")
