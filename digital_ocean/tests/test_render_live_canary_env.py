from __future__ import annotations

import stat
from pathlib import Path

from digital_ocean.scripts.python.render_live_canary_env import render

ROOT = Path(__file__).resolve().parents[2]


def parsed(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value
    return result


def test_canary_env_is_private_secret_randomized_and_staging_only(tmp_path):
    target = tmp_path / "canary.env"
    render(ROOT / ".env.example", target, "f093-abc.example.com", "base2-f093-t1")
    values = parsed(target)
    text = target.read_text(encoding="utf-8")
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert "YOUR_" not in text
    assert "your_" not in text
    assert values["WEBSITE_DOMAIN"] == "f093-abc.example.com"
    assert values["PROJECT_NAME"] == "base2-f093-t1"
    assert values["TRAEFIK_CANARY_MODE"] == "true"
    assert values["TRAEFIK_CERT_RESOLVER"] == "le-staging"
    assert values["ENV"] == "production"
    assert values["DEBUG"] == "false"
    assert values["API_DOCS_ENABLED"] == "false"
    for key in (
        "TP_DJANGO_SECRET_KEY",
        "TP_JWT_SECRET",
        "TP_TOKEN_PEPPER",
        "TP_IDENTITY_ENCRYPTION_KEY",
        "TP_CONTENT_WORKSPACE_STORAGE_KEY",
        "TP_POSTGRES_PASSWORD",
        "TP_REDIS_PASSWORD",
        "TP_PGADMIN_PASSWORD",
    ):
        assert len(values[key]) >= 32
        assert values[key] != "fixture"
    assert len(values["TP_IDENTITY_ENCRYPTION_KEY"]) == 44
    assert len(values["TP_CONTENT_WORKSPACE_STORAGE_KEY"]) == 44


def test_invalid_domain_or_project_fails_before_write(tmp_path):
    target = tmp_path / "canary.env"
    for domain, project in (("bad.invalid", "base2-good"), ("example.com", "../bad")):
        try:
            render(ROOT / ".env.example", target, domain, project)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe canary identity was accepted")
        assert not target.exists()
