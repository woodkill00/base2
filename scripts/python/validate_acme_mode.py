#!/usr/bin/env python3
"""Fail closed unless Base2's Traefik boundary is staging-only."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

STAGING_ENDPOINT = "https://acme-staging-v02.api.letsencrypt.org/directory"
LIVE_ENDPOINT = "acme-v02.api.letsencrypt.org"
STAGING_STORAGE = "/etc/traefik/acme/acme-staging.json"


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    static = (root / "traefik/traefik.yml").read_text(encoding="utf-8")
    entrypoint = (root / "traefik/entrypoint.sh").read_text(encoding="utf-8")
    example = (root / ".env.example").read_text(encoding="utf-8")
    deploy = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    remote_test = (root / "digital_ocean/scripts/powershell/test.ps1").read_text(encoding="utf-8")
    smoke = (root / "digital_ocean/scripts/powershell/smoke-tests.ps1").read_text(encoding="utf-8")

    if static.count(STAGING_ENDPOINT) != 1:
        errors.append("static config must contain the exact staging endpoint once")
    without_staging = static.replace(STAGING_ENDPOINT, "")
    if LIVE_ENDPOINT in without_staging:
        errors.append("static config references the live Let's Encrypt endpoint")
    if re.search(r"(?m)^\s{2}le:\s*$", static):
        errors.append("static config defines the live le resolver")
    if STAGING_STORAGE not in static:
        errors.append("static config does not use isolated staging storage")
    if re.search(r"storage:\s*/etc/traefik/acme/acme\.json", static):
        errors.append("static config selects live ACME storage")
    if "TRAEFIK_CERT_RESOLVER=le-staging" not in example:
        errors.append("example environment is not staging-only")
    if "expected = 'le-staging'" not in deploy:
        errors.append("deployment does not force the staging resolver")
    if "expectedResolver = 'le-staging'" not in remote_test:
        errors.append("remote validation does not require the staging resolver")
    if "TLS issuer is not recognizably staging-only" not in smoke:
        errors.append("smoke validation does not reject a non-staging issuer")
    if "must remain le-staging" not in entrypoint:
        errors.append("entrypoint does not reject resolver overrides")
    if 'TRAEFIK_CERT_RESOLVER="le"' in entrypoint:
        errors.append("entrypoint can select the live resolver")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    errors = validate(root)
    print(json.dumps({"ok": not errors, "mode": "staging-only", "errors": errors}))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
