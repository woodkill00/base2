#!/usr/bin/env python3
"""Render an exact, redacted Feature 093 live-canary proposal without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from digital_ocean.scripts.python.deploy_config import parse_env_text
except ModuleNotFoundError:
    from deploy_config import parse_env_text

TEMPLATE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
SAFE_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
SAFE_DOMAIN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SECRET_MARKERS = ("TOKEN", "PASSWORD", "SECRET", "PRIVATE", "CREDENTIAL")
BINDING_FIELDS = (
    "sourceCommit",
    "sourceArchiveSha256",
    "projectName",
    "providerProjectId",
    "region",
    "size",
    "image",
    "dropletName",
    "ownershipNamespace",
    "dnsZone",
    "dnsMutations",
    "certificateSans",
    "trialCount",
    "maximumConcurrentDroplets",
    "leaseMinutesPerTrial",
    "totalCostCeilingMinorUnits",
    "hourlyCostMinorUnitsCeiling",
    "currency",
    "certificateMode",
)


class PreflightError(RuntimeError):
    pass


def _commit(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise PreflightError("an exact lowercase source commit is required")
    return commit


def _archive_digest(repo_root: Path, commit: str) -> str:
    result = subprocess.run(
        ["git", "archive", "--format=tar", commit],
        cwd=repo_root,
        check=True,
        capture_output=True,
        timeout=30,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def _resolve(values: dict[str, str], value: str) -> str:
    current = str(value or "")
    for _ in range(8):
        updated = TEMPLATE.sub(lambda match: values.get(match.group(1), match.group(0)), current)
        if updated == current:
            break
        current = updated
    if "${" in current or "YOUR_" in current:
        return ""
    return current.strip()


def _choose(values: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        candidate = _resolve(values, values.get(key, ""))
        if candidate:
            return candidate
    return default


def binding_digest(binding: dict[str, Any]) -> str:
    if set(binding) != set(BINDING_FIELDS):
        raise PreflightError("plan binding fields are not exact")
    return hashlib.sha256(
        json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_plan(env_path: Path, repo_root: Path) -> dict[str, Any]:
    if not env_path.is_file() or env_path.is_symlink():
        raise PreflightError("environment source must be a real file")
    values = parse_env_text(env_path.read_text(encoding="utf-8-sig"))
    commit = _commit(repo_root)
    archive_digest = _archive_digest(repo_root, commit)
    project = _choose(values, "PROJECT_NAME", default="base2").lower()
    domain = _choose(values, "DO_DOMAIN", "WEBSITE_DOMAIN", "DO_DNS_DOMAIN").lower()
    region = _choose(values, "DO_API_REGION", "DO_DROPLET_REGION", default="nyc3")
    size = _choose(values, "DO_API_SIZE", "DO_DROPLET_SIZE", default="s-1vcpu-1gb")
    image = _choose(
        values, "DO_API_IMAGE", "DO_DROPLET_IMAGE", default="ubuntu-24-04-x64"
    )
    project_id = _choose(values, "DO_PROJECT_ID", default="not-configured")
    try:
        hourly_cost_ceiling = int(
            _choose(
                values,
                "DO_CANARY_HOURLY_COST_MINOR_UNITS_CEILING",
                default="100",
            )
        )
    except ValueError as exc:
        raise PreflightError("hourly cost ceiling is invalid") from exc
    if not 1 <= hourly_cost_ceiling <= 100:
        raise PreflightError("hourly cost ceiling is invalid")
    if not SAFE_NAME.fullmatch(project):
        raise PreflightError("project name is unsafe")
    reserved_suffixes = (".invalid", ".test", ".example", ".localhost")
    if not SAFE_DOMAIN.fullmatch(domain) or domain.endswith(reserved_suffixes):
        raise PreflightError("an exact public DNS zone is required")
    for label, value in (("region", region), ("size", size), ("image", image)):
        if not SAFE_SLUG.fullmatch(value):
            raise PreflightError(f"{label} is unsafe")
    token_present = bool(values.get("DO_API_TOKEN") or values.get("DIGITAL_OCEAN_API_TOKEN"))
    canary_label = f"f093-{commit[:8]}"
    dns_name = f"{canary_label}.{domain}"
    safe_binding = {
        "sourceCommit": commit,
        "sourceArchiveSha256": archive_digest,
        "projectName": project,
        "providerProjectId": project_id,
        "region": region,
        "size": size,
        "image": image,
        "dropletName": f"{project}-{canary_label}",
        "ownershipNamespace": f"base2-f093-{commit[:8]}",
        "dnsZone": domain,
        "dnsMutations": [{"name": canary_label, "type": "A", "fqdn": dns_name}],
        "certificateSans": [dns_name],
        "trialCount": 3,
        "maximumConcurrentDroplets": 1,
        "leaseMinutesPerTrial": 15,
        "totalCostCeilingMinorUnits": 100,
        "hourlyCostMinorUnitsCeiling": hourly_cost_ceiling,
        "currency": "USD",
        "certificateMode": "letsencrypt-staging-only",
    }
    digest = binding_digest(safe_binding)
    return {
        "schemaVersion": 1,
        "status": "approval-required",
        "networkRequests": 0,
        "credentialSourceFilesRead": 1,
        "credentialConfigured": token_present,
        "secretValuesEmitted": 0,
        "planDigest": digest,
        **safe_binding,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args(argv)
    plan = build_plan(args.env_path.resolve(), args.repo_root.resolve())
    rendered = json.dumps(plan, indent=2, sort_keys=True)
    if any(marker in rendered.upper() for marker in SECRET_MARKERS):
        # Only the fixed non-secret counters above may contain marker words.
        parsed = json.loads(rendered)
        forbidden = [
            key
            for key in parsed
            if any(marker in key.upper() for marker in SECRET_MARKERS)
            and key
            not in {
                "credentialSourceFilesRead",
                "credentialConfigured",
                "secretValuesEmitted",
            }
        ]
        if forbidden:
            raise PreflightError("preflight output contains a secret-bearing field")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
