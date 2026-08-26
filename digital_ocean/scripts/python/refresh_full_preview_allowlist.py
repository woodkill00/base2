#!/usr/bin/env python3
"""Apply one exact owner-approved allowlist refresh to a private preview env."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

from digital_ocean.scripts.python.deploy_config import parse_env_text
from digital_ocean.scripts.python.full_preview_policy import validate_owner_cidrs
from digital_ocean.scripts.python.preview_lease_v2 import RUN_ID


class AllowlistRefreshError(RuntimeError):
    pass


def approval_digest(run_id: str, cidrs: list[str]) -> str:
    normalized = list(validate_owner_cidrs(cidrs))
    payload = {"action": "refresh-full-preview-owner-allowlist", "ownerCidrs": normalized, "runId": run_id}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def refresh(path: Path, run_id: str, cidrs: list[str], approved_digest: str) -> dict:
    if not RUN_ID.fullmatch(run_id):
        raise AllowlistRefreshError("run ID is invalid")
    normalized = list(validate_owner_cidrs(cidrs))
    expected = approval_digest(run_id, normalized)
    if approved_digest != expected:
        raise AllowlistRefreshError("exact owner approval digest does not match")
    if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise AllowlistRefreshError("private preview environment is unsafe")
    values = parse_env_text(path.read_text(encoding="utf-8"))
    if values.get("TRAEFIK_PREVIEW_MODE") != "full-preview":
        raise AllowlistRefreshError("target is not an active full-preview environment")
    values["OWNER_ALLOWLIST_CSV"] = ",".join(normalized)
    for key in ("DJANGO_ADMIN_ALLOWLIST", "PGADMIN_ALLOWLIST", "FLOWER_ALLOWLIST"):
        values[key] = normalized[0]
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)
    return {"ok": True, "runId": run_id, "ownerCidrCount": len(normalized), "ownerAdmissionDigest": hashlib.sha256(",".join(normalized).encode()).hexdigest(), "secretValuesEmitted": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--owner-cidr", action="append", required=True)
    parser.add_argument("--approval-digest", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(refresh(args.env_file, args.run_id, args.owner_cidr, args.approval_digest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
