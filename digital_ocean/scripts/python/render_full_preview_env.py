#!/usr/bin/env python3
"""Render a private full-preview Compose environment without emitting secrets."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from digital_ocean.scripts.python.deploy_config import parse_env_text
from digital_ocean.scripts.python.full_preview_policy import PolicyError, validate_owner_cidrs
from digital_ocean.scripts.python.render_live_canary_env import render as render_private_base


AUTH = re.compile(r"^[A-Za-z0-9._-]{1,64}:(?:\$apr1\$[^\s:]{3,128}|\$2[aby]\$[0-9]{2}\$[^\s:]{53})$")
DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


class RenderError(ValueError): pass


def _auth(value: str, label: str) -> str:
    if not isinstance(value, str) or "\n" in value or "\r" in value or not AUTH.fullmatch(value):
        raise RenderError(f"{label} basic-auth value is invalid")
    return value.replace("$", "$$")


def _write_env(path: Path, values: dict[str, str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def render(source: Path, target: Path, domain: str, project: str, owner_cidrs: list[str], *, operator_basic_auth: str, flower_basic_auth: str) -> dict:
    domain = str(domain).strip().lower()
    if not DOMAIN.fullmatch(domain):
        raise RenderError("preview domain is invalid")
    try:
        cidrs = validate_owner_cidrs(owner_cidrs)
    except PolicyError as exc:
        raise RenderError(str(exc)) from exc
    operator = _auth(operator_basic_auth, "operator")
    flower = _auth(flower_basic_auth, "flower")
    if operator.split(":", 1)[1] == flower.split(":", 1)[1]:
        raise RenderError("operator and Flower credentials must be independent")
    staging = target.with_suffix(target.suffix + ".base")
    render_private_base(source, staging, domain, project)
    values = parse_env_text(staging.read_text(encoding="utf-8"))
    staging.unlink(missing_ok=True)
    values.update({
        "PROJECT_NAME": project,
        "COMPOSE_PROJECT_NAME": project,
        "WEBSITE_DOMAIN": domain,
        "SITE_PROFILE": "base2-obsidian",
        "TRAEFIK_PREVIEW_MODE": "full-preview",
        "TRAEFIK_CANARY_MODE": "false",
        "TRAEFIK_CERT_RESOLVER": "le-staging",
        "API_DOCS_ENABLED": "true",
        "OWNER_ALLOWLIST_CSV": ",".join(cidrs),
        "DJANGO_ADMIN_ALLOWLIST": cidrs[0],
        "PGADMIN_ALLOWLIST": cidrs[0],
        "FLOWER_ALLOWLIST": cidrs[0],
        "DJANGO_ALLOWED_HOSTS": f"{domain},admin.{domain},django,api",
        "CORS_ALLOW_ORIGINS": f"https://{domain}",
        "FRONTEND_URL": f"https://{domain}",
        "TRAEFIK_DASH_BASIC_USERS": operator,
        "FLOWER_BASIC_USERS": flower,
    })
    _write_env(target, values)
    return {"ok": True, "mode": "full-preview", "secretValuesEmitted": 0, "ownerCidrCount": len(cidrs)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--owner-cidr", action="append", required=True)
    parser.add_argument("--operator-basic-auth-file", type=Path, required=True)
    parser.add_argument("--flower-basic-auth-file", type=Path, required=True)
    args = parser.parse_args(argv)
    operator = args.operator_basic_auth_file.read_text(encoding="utf-8").strip()
    flower = args.flower_basic_auth_file.read_text(encoding="utf-8").strip()
    receipt = render(args.source, args.target, args.domain, args.project, args.owner_cidr, operator_basic_auth=operator, flower_basic_auth=flower)
    print('{"mode":"full-preview","ok":true,"ownerCidrCount":%d,"secretValuesEmitted":0}' % receipt["ownerCidrCount"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
