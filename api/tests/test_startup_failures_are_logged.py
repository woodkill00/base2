import importlib
import os
import sys

import pytest


def test_settings_import_failure_is_loud(monkeypatch, caplog):
    monkeypatch.setenv("ENV", "production")
    # Ensure missing criticals to trigger failure
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("TOKEN_PEPPER", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    # Reload module under fresh import
    if "api.main" in sys.modules:
        del sys.modules["api.main"]
    caplog.set_level("ERROR")
    with pytest.raises(Exception):
        importlib.import_module("api.main")
    msgs = "\n".join(r.getMessage() for r in caplog.records)
    assert "settings_import_failed" in msgs or "Missing required env var" in msgs
