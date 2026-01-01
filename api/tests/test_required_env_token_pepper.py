from __future__ import annotations

import importlib
import sys
import pytest


def test_settings_requires_token_pepper_in_staging(monkeypatch):
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("FRONTEND_URL", "https://example.com")
    monkeypatch.setenv("OAUTH_STATE_SECRET", "state-secret")
    monkeypatch.delenv("TOKEN_PEPPER", raising=False)

    # Ensure we re-evaluate module import-time validation.
    sys.modules.pop("api.settings", None)

    with pytest.raises(RuntimeError) as exc:
        importlib.import_module("api.settings")
    assert "TOKEN_PEPPER" in str(exc.value)
