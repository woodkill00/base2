from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]


def test_synthetic_app_fails_closed_without_mode_or_key():
    environment = os.environ.copy()
    environment.pop("E2E_TEST_MODE", None)
    environment.pop("E2E_TEST_KEY", None)
    result = subprocess.run(
        [sys.executable, "-c", "import api.synthetic_support_app"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "test_support_mode_required" in result.stderr

    environment["E2E_TEST_MODE"] = "true"
    result = subprocess.run(
        [sys.executable, "-c", "import api.synthetic_support_app"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "test_support_key_required" in result.stderr


def test_synthetic_app_exposes_only_the_keyed_support_route(monkeypatch):
    monkeypatch.setenv("E2E_TEST_MODE", "true")
    monkeypatch.setenv("E2E_TEST_KEY", "synthetic-key")
    sys.modules.pop("api.synthetic_support_app", None)
    from api.synthetic_support_app import app

    client = TestClient(app)
    assert (
        client.get("/api/test-support/outbox/latest?to_email=x%40example.invalid").status_code
        == 401
    )
    assert client.get("/api/health").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_synthetic_app_is_absent_from_production_profiles():
    production_sources = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("local.docker.yml", "development.docker.yml")
    )
    assert "api.synthetic_support_app" not in production_sources


def test_synthetic_app_is_not_a_pytest_collection_candidate() -> None:
    assert not (ROOT / "api/synthetic_support_app.py").name.startswith("test")
