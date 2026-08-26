#!/usr/bin/env python3
"""Integrity-checked private inventory for Base2 full-preview leases."""

from __future__ import annotations

import os
import stat
from datetime import UTC, datetime
from pathlib import Path

from digital_ocean.scripts.python.preview_lease_v2 import FullPreviewLeaseStore


class InventoryError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def admit_private_root(root: str | os.PathLike[str], *, create: bool = False) -> Path:
    path = Path(root)
    if create and not path.exists():
        path.mkdir(parents=True, mode=0o700)
    if path.is_symlink() or not path.is_dir():
        raise InventoryError("STATE_PERMISSION_INVALID", "state root must be a real directory")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise InventoryError("STATE_PERMISSION_INVALID", "state root must be owner-only")
    return path.resolve(strict=True)


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise InventoryError("LEASE_INTEGRITY_INVALID", "lease timestamp is invalid") from exc
    return parsed.astimezone(UTC)


def inventory(root: str | os.PathLike[str], *, now: datetime | None = None) -> dict:
    state_root = admit_private_root(root)
    observed = (now or datetime.now(UTC)).astimezone(UTC)
    valid: list[dict] = []
    invalid: list[dict] = []
    seen: dict[str, str] = {}
    for path in sorted(state_root.glob("base2-full-*/leases/*.json"), key=lambda item: str(item)):
        relative = str(path.relative_to(state_root))
        if path.is_symlink() or path.parent.is_symlink():
            invalid.append({"path": relative, "code": "LEASE_INTEGRITY_INVALID"})
            continue
        run_id = path.stem
        try:
            lease = FullPreviewLeaseStore(path.parent).load(run_id)
        except Exception:
            invalid.append({"path": relative, "code": "LEASE_INTEGRITY_INVALID"})
            continue
        if run_id in seen:
            invalid.append({"path": relative, "code": "LEASE_CONFLICT"})
            continue
        seen[run_id] = relative
        effective = lease["state"]
        if effective == "live-verified" and _parse_time(lease["expiresAt"]) <= observed:
            effective = "expired"
        exact_addresses = sorted(
            {
                record["value"]
                for record in lease.get("dnsRecords") or []
                if record.get("type") == "A" and record.get("value")
            }
        )
        valid.append(
            {
                "runId": run_id,
                "state": lease["state"],
                "effectiveState": effective,
                "sourceCommit": lease["sourceCommit"],
                "expiresAt": lease["expiresAt"],
                "dropletId": (lease.get("droplet") or {}).get("id"),
                "dnsRecordCount": len(lease.get("dnsRecords") or []),
                "exactAddress": exact_addresses[0] if len(exact_addresses) == 1 else None,
                "mutationCounts": lease["mutationCounts"],
                "path": relative,
            }
        )
    valid.sort(key=lambda row: row["runId"])
    counts: dict[str, int] = {}
    for row in valid:
        counts[row["effectiveState"]] = counts.get(row["effectiveState"], 0) + 1
    unresolved = [row["runId"] for row in valid if row["effectiveState"] != "destroyed"]
    code = "OK"
    if invalid:
        code = "LEASE_INTEGRITY_INVALID"
    elif len(unresolved) > 1:
        code = "LEASE_CONFLICT"
    return {
        "schemaVersion": 1,
        "ok": code == "OK",
        "code": code,
        "stateRoot": str(state_root),
        "leases": valid,
        "invalid": invalid,
        "counts": dict(sorted(counts.items())),
        "unresolvedRunIds": unresolved,
        "credentialReads": 0,
        "providerActions": 0,
        "secretValuesEmitted": 0,
    }
