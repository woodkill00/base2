#!/usr/bin/env python3
"""Render a private, ephemeral Compose environment for a live staging canary."""

from __future__ import annotations

import argparse
import base64
import os
import re
import secrets
from pathlib import Path

SAFE_PROJECT = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
SAFE_DOMAIN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
PLACEHOLDER = re.compile(r"\b(?:YOUR_[A-Z0-9_]+|your_[a-z0-9_]+)\b")
RESERVED = (".invalid", ".test", ".example", ".localhost")
SECRET_KEYS = {
    "USER_MAIN_PASSWORD",
    "TP_DJANGO_SECRET_KEY",
    "TP_JWT_SECRET",
    "TP_TOKEN_PEPPER",
    "TP_OAUTH_STATE_SECRET",
    "TP_SEED_ADMIN_PASSWORD",
    "TP_SEED_DEMO_PASSWORD",
    "TP_DJANGO_SUPERUSER_PASSWORD",
    "TP_REDIS_PASSWORD",
    "TP_POSTGRES_PASSWORD",
    "TP_WORKSPACE_DB_PASSWORD",
    "TP_PGADMIN_PASSWORD",
    "TP_FLOWER_PASSWORD",
    "TP_TRAEFIK_PASSWORD",
    "TP_EMAIL_HOST_PASSWORD",
    "GOOGLE_OAUTH_CLIENT_SECRET",
}


def _secret() -> str:
    return secrets.token_urlsafe(32)


def _fernet_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


def render(source: Path, target: Path, domain: str, project: str) -> None:
    domain = domain.strip().lower()
    project = project.strip().lower()
    if not SAFE_DOMAIN.fullmatch(domain) or domain.endswith(RESERVED):
        raise ValueError("exact public canary domain is required")
    if not SAFE_PROJECT.fullmatch(project):
        raise ValueError("safe canary project name is required")
    if not source.is_file() or source.is_symlink():
        raise ValueError("environment template must be a real file")

    overrides = {
        "PROJECT_NAME": project,
        "WEBSITE_DOMAIN": domain,
        "ENV": "production",
        "DEPLOY_MODE": "canary",
        "USER_MAIN_EMAIL": f"canary@{domain}",
        "USER_MAIN_NAME": "canary",
        "TP_USER_IP_ADDRESS": "127.0.0.1",
        "GIT_REPO": "https://example.com/disabled.git",
        "GIT_REPO_BRANCH": "disabled",
        "DEBUG_ENABLED": "false",
        "DEBUG": "false",
        "DEBUG_LEVEL": "INFO",
        "API_DOCS_ENABLED": "false",
        "DJANGO_DEBUG": "false",
        "DJANGO_ALLOW_ALL_HOSTS": "false",
        "DJANGO_ALLOWED_HOSTS": f"{domain},django,api",
        "FLOWER_BASIC_USERS": "disabled",
        "TRAEFIK_DASH_BASIC_USERS": "disabled",
        "REACT_APP_GOOGLE_CLIENT_ID": "disabled",
        "GOOGLE_OAUTH_CLIENT_ID": "disabled",
        "DIGITAL_OCEAN_API_TOKEN": "disabled",
        "DIGITAL_OCEAN_SSH_KEY_ID": "disabled",
        "DIGITAL_OCEAN_API_SSH_KEYS": "disabled",
        "TRAEFIK_CERT_RESOLVER": "le-staging",
        "TRAEFIK_CANARY_MODE": "true",
    }
    overrides.update({key: _secret() for key in SECRET_KEYS})
    overrides["TP_IDENTITY_ENCRYPTION_KEY"] = _fernet_key()
    overrides["TP_CONTENT_WORKSPACE_STORAGE_KEY"] = _fernet_key()

    rendered: list[str] = []
    seen: set[str] = set()
    for raw in source.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw:
            rendered.append(raw)
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        seen.add(key)
        replacement = overrides.get(key, PLACEHOLDER.sub("fixture", value))
        rendered.append(f"{key}={replacement}")
    for key in sorted(set(overrides) - seen):
        rendered.append(f"{key}={overrides[key]}")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text("\n".join(rendered) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args(argv)
    render(args.source, args.target, args.domain, args.project)
    print('{"ok":true,"secretValuesEmitted":0}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
