from __future__ import annotations

from fastapi import APIRouter

from api.settings import settings

router = APIRouter(prefix="/identity", tags=["identity"])


@router.get("/capabilities")
async def identity_capabilities():
    google_ready = bool(
        settings.GOOGLE_OAUTH_ENABLED
        and settings.GOOGLE_OAUTH_CLIENT_ID
        and settings.GOOGLE_OAUTH_CLIENT_SECRET
        and settings.GOOGLE_OAUTH_REDIRECT_URI
        and settings.OAUTH_STATE_SECRET
    )
    return {
        "account": {
            "password": {"enabled": True},
            "google_oauth": {"enabled": google_ready, "version": "v1"},
        },
        "mfa": {
            "totp": {"enabled": True, "version": "v1"},
            "recovery_codes": {"enabled": True, "version": "v1"},
            "webauthn": {"enabled": bool(settings.WEBAUTHN_ENABLED), "version": "v1"},
        },
    }
