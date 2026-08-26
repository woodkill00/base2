#!/usr/bin/env python3
"""Fixed exact-run expiry planning and optional WSL user-timer installation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from digital_ocean.scripts.python.preview_lease_v2 import RUN_ID, FullPreviewLeaseStore

UNIT = re.compile(r"^[a-zA-Z0-9_.@-]+$")


class ExpiryPlanError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _systemd_calendar(value: str) -> str:
    """Convert the signed RFC 3339 lease expiry to portable systemd syntax."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except (AttributeError, ValueError) as exc:
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "expiry timestamp is invalid") from exc
    return parsed.strftime("%Y-%m-%d %H:%M:%S UTC")


def _private_file(path: str | os.PathLike[str], label: str) -> Path:
    candidate = Path(path)
    if (
        candidate.is_symlink()
        or not candidate.is_file()
        or stat.S_IMODE(candidate.stat().st_mode) & 0o077
    ):
        raise ExpiryPlanError(
            "STATE_PERMISSION_INVALID", f"{label} must be an owner-only real file"
        )
    return candidate.resolve(strict=True)


def build_expiry_plan(
    *,
    lease_root: str | os.PathLike[str],
    run_id: str,
    credential_file: str | os.PathLike[str],
    python_executable: str | os.PathLike[str],
    repo_root: str | os.PathLike[str],
) -> dict:
    if not RUN_ID.fullmatch(run_id):
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "run ID is invalid")
    root = Path(lease_root)
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise ExpiryPlanError("STATE_PERMISSION_INVALID", "lease root must be owner-only")
    lease = FullPreviewLeaseStore(root).load(run_id)
    if lease["state"] != "live-verified":
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "only a live verified lease can be armed")
    credential = _private_file(credential_file, "credential file")
    python = Path(python_executable).resolve(strict=True)
    repo = Path(repo_root).resolve(strict=True)
    module = repo / "digital_ocean/scripts/python/full_preview_expire.py"
    if not str(repo).startswith("/home/") or not module.is_file() or module.is_symlink():
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "stable expiry module is unavailable")
    unit = f"base2-full-preview-expiry-{run_id}"
    if not UNIT.fullmatch(unit):
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "timer identity is invalid")
    command = [
        str(python),
        "-m",
        "digital_ocean.scripts.python.full_preview_expire",
        "--state-root",
        str(root.resolve(strict=True)),
        "--run-id",
        run_id,
        "--credential-file",
        str(credential),
    ]
    plan = {
        "schemaVersion": 1,
        "runId": run_id,
        "expiresAt": lease["expiresAt"],
        "unit": unit,
        "repository": str(repo),
        "moduleSha256": hashlib.sha256(module.read_bytes()).hexdigest(),
        "credentialPathSha256": hashlib.sha256(str(credential).encode()).hexdigest(),
        "command": command,
        "persistent": True,
        "catchUpAfterRestart": True,
        "secretValuesEmitted": 0,
    }
    plan["planDigest"] = _digest(plan)
    return plan


def systemd_run_arguments(plan: dict) -> list[str]:
    if plan.get("planDigest") != _digest({k: v for k, v in plan.items() if k != "planDigest"}):
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "expiry plan digest mismatch")
    return [
        "systemd-run",
        "--user",
        f"--unit={plan['unit']}",
        f"--on-calendar={_systemd_calendar(plan['expiresAt'])}",
        "--timer-property=Persistent=true",
        "--property=UMask=0077",
        "--working-directory",
        plan["repository"],
        "--",
        *plan["command"],
    ]


def arm_expiry(plan: dict, *, runner: Callable = subprocess.run) -> dict:
    args = systemd_run_arguments(plan)
    completed = runner(args, check=False, capture_output=True, text=True, timeout=20)
    if completed.returncode != 0:
        raise ExpiryPlanError("EXPIRY_NOT_ARMED", "persistent expiry timer could not be armed")
    verified = verify_expiry(plan, runner=runner)
    return {
        "schemaVersion": 1,
        "ok": True,
        "code": "OK",
        "runId": plan["runId"],
        "unit": plan["unit"] + ".timer",
        "expiresAt": plan["expiresAt"],
        "planDigest": plan["planDigest"],
        "armed": True,
        "persistent": True,
        "controllerCoverage": {"primary": "armed", "backup": "not-configured"},
        "verification": verified,
        "secretValuesEmitted": 0,
    }


def verify_expiry(plan: dict, *, runner: Callable = subprocess.run) -> dict:
    systemd_run_arguments(plan)
    completed = runner(
        [
            "systemctl",
            "--user",
            "show",
            plan["unit"] + ".timer",
            "--property=ActiveState",
            "--property=LoadState",
            "--no-pager",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    fields = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            fields[key] = value
    if (
        completed.returncode != 0
        or fields.get("LoadState") != "loaded"
        or fields.get("ActiveState") != "active"
    ):
        raise ExpiryPlanError("EXPIRY_NOT_ARMED", "persistent expiry timer did not verify active")
    return {"unit": plan["unit"] + ".timer", "loadState": "loaded", "activeState": "active"}


def extend_lease(
    *,
    lease_root: str | os.PathLike[str],
    run_id: str,
    minutes: int,
    now: datetime | None = None,
    maximum_total_minutes: int = 120,
) -> dict:
    if not isinstance(minutes, int) or not 1 <= minutes <= 60:
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "extension must be between 1 and 60 minutes")
    store = FullPreviewLeaseStore(lease_root)
    lease = store.load(run_id)
    if lease["state"] != "live-verified":
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "only a live verified lease can be extended")
    current = (now or datetime.now(UTC)).astimezone(UTC)
    armed = datetime.fromisoformat(lease["armedAt"].replace("Z", "+00:00")).astimezone(UTC)
    old_expiry = datetime.fromisoformat(lease["expiresAt"].replace("Z", "+00:00")).astimezone(UTC)
    if old_expiry <= current:
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "expired lease cannot be extended")
    new_expiry = old_expiry + timedelta(minutes=minutes)
    if new_expiry > armed + timedelta(minutes=maximum_total_minutes):
        raise ExpiryPlanError("EXPIRY_PLAN_DRIFT", "extension exceeds maximum total lease")
    lease["expiresAt"] = new_expiry.isoformat().replace("+00:00", "Z")
    store.replace(lease)
    return {
        "schemaVersion": 1,
        "ok": True,
        "code": "OK",
        "runId": run_id,
        "previousExpiresAt": old_expiry.isoformat().replace("+00:00", "Z"),
        "expiresAt": lease["expiresAt"],
        "providerActions": 0,
        "secretValuesEmitted": 0,
    }
