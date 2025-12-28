from __future__ import annotations

import importlib
import os


def test_settings_requires_token_pepper_in_staging(monkeypatch):
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("FRONTEND_URL", "https://example.com")
    monkeypatch.setenv("OAUTH_STATE_SECRET", "state-secret")
    monkeypatch.delenv("TOKEN_PEPPER", raising=False)

    try:
        importlib.import_module("api.settings")
        assert False, "Expected settings import to fail without TOKEN_PEPPER in staging"
    except RuntimeError as e:
        assert "TOKEN_PEPPER" in str(e)
