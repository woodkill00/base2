import importlib
import os
import sys

import pytest


def test_settings_import_failure_is_loud(monkeypatch, caplog, capsys):
    monkeypatch.setenv("ENV", "production")
    # Ensure missing criticals (explicitly blank to override any .env)
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setenv("TOKEN_PEPPER", "")
    monkeypatch.setenv("FRONTEND_URL", "")
    monkeypatch.setenv("OAUTH_STATE_SECRET", "")
    # Reload module under fresh import
    if "api.main" in sys.modules:
        del sys.modules["api.main"]
    caplog.set_level("ERROR")
    with pytest.raises(Exception):
        importlib.import_module("api.main")
    # Prefer captured stdout/stderr since logging may emit to stream handlers
    out = capsys.readouterr()
    stream_msgs = (out.out or "") + "\n" + (out.err or "")
    msgs = "\n".join(r.getMessage() for r in caplog.records)
    combined = msgs + "\n" + stream_msgs
    assert "settings_import_failed" in combined or "Missing required env var" in combined
