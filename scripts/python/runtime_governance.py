#!/usr/bin/env python3
"""Pure fail-closed contracts for secrets, jobs, schedules, audit, and notifications."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
SECRET_REF = re.compile(r"^vaultwarden://[a-z][a-z0-9-]{2,62}/[a-z][a-z0-9_.-]{2,127}#[a-z][a-z0-9_.-]{1,63}$")
SENSITIVE = re.compile(r"token|password|secret|credential|authorization|cookie|private.?key", re.I)


class RuntimeGovernanceError(ValueError):
    pass


def validate_credential_inventory(value: Any) -> list[dict[str, Any]]:
    required = {"class", "owner", "scope", "source", "consumer", "lifetimeSeconds", "rotation", "revocation", "recovery"}
    if not isinstance(value, list) or not value:
        raise RuntimeGovernanceError("secret:inventory_invalid")
    seen = set()
    result = []
    for item in value:
        if not isinstance(item, dict) or set(item) != required:
            raise RuntimeGovernanceError("secret:inventory_invalid")
        if item["class"] in seen or not all(
            isinstance(item[key], str) and item[key] and not SENSITIVE.search(item[key])
            for key in required - {"lifetimeSeconds"}
        ):
            raise RuntimeGovernanceError("secret:inventory_invalid")
        if type(item["lifetimeSeconds"]) is not int or not 60 <= item["lifetimeSeconds"] <= 31_536_000:
            raise RuntimeGovernanceError("secret:inventory_invalid")
        seen.add(item["class"])
        result.append(dict(item))
    return result


def secret_reference(value: str) -> str:
    if not SECRET_REF.fullmatch(value or ""):
        raise RuntimeGovernanceError("secret:reference_invalid")
    return value


def credential_rotation(*, current_generation: int, action: str, consumers_ready: bool) -> dict[str, Any]:
    if current_generation < 1 or action not in {"begin", "promote", "revoke_old"}:
        raise RuntimeGovernanceError("secret:rotation_invalid")
    if action in {"promote", "revoke_old"} and not consumers_ready:
        raise RuntimeGovernanceError("secret:consumer_not_ready")
    return {
        "generation": current_generation + (1 if action == "begin" else 0),
        "state": {"begin": "overlap", "promote": "promoted", "revoke_old": "complete"}[action],
        "restartRequired": action == "promote",
    }


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if SENSITIVE.search(str(key)) else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def append_audit(chain: list[dict[str, Any]], event: dict[str, Any], key: bytes) -> dict[str, Any]:
    required = {"tenantId", "actorRef", "action", "targetRef", "outcome", "occurredAt"}
    if set(event) != required or len(key) < 32 or any(SENSITIVE.search(str(k)) for k in event):
        raise RuntimeGovernanceError("audit:event_invalid")
    prior = chain[-1]["entryDigest"] if chain else "0" * 64
    body = {**event, "priorDigest": prior}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["entryDigest"] = hmac.new(key, canonical, hashlib.sha256).hexdigest()
    return body


def verify_audit(chain: list[dict[str, Any]], key: bytes) -> bool:
    prior = "0" * 64
    for item in chain:
        body = {k: v for k, v in item.items() if k != "entryDigest"}
        if body.get("priorDigest") != prior:
            raise RuntimeGovernanceError("audit:chain_invalid")
        expected = hmac.new(
            key, json.dumps(body, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, item.get("entryDigest", "")):
            raise RuntimeGovernanceError("audit:chain_invalid")
        prior = expected
    return True


def claim_job(job: dict[str, Any], *, worker: str, now: datetime, lease_seconds: int = 60) -> dict[str, Any]:
    if job.get("state") not in {"queued", "retry", "leased"} or not IDENTIFIER.fullmatch(worker or ""):
        raise RuntimeGovernanceError("job:claim_invalid")
    if now.tzinfo is None or not 1 <= lease_seconds <= 900:
        raise RuntimeGovernanceError("job:claim_invalid")
    value = dict(job)
    expiry = datetime.fromisoformat(value["leaseExpiresAt"]) if value.get("leaseExpiresAt") else None
    if value["state"] == "leased" and expiry and expiry > now:
        if value.get("leaseOwner") == worker:
            return value
        raise RuntimeGovernanceError("job:already_leased")
    if int(value.get("attempts", 0)) >= int(value.get("maximumAttempts", 5)):
        value.update(state="dead_letter", leaseOwner="", leaseExpiresAt=None)
        return value
    value.update(
        state="leased", leaseOwner=worker, leaseExpiresAt=(now + timedelta(seconds=lease_seconds)).isoformat(),
        attempts=int(value.get("attempts", 0)) + 1,
    )
    return value


def settle_job(job: dict[str, Any], *, worker: str, outcome: str, now: datetime) -> dict[str, Any]:
    if job.get("state") != "leased" or job.get("leaseOwner") != worker or outcome not in {"success", "retry", "fail"}:
        raise RuntimeGovernanceError("job:settle_invalid")
    value = dict(job)
    value.update(leaseOwner="", leaseExpiresAt=None)
    if outcome == "success":
        value["state"] = "succeeded"
    elif outcome == "retry" and value["attempts"] < value.get("maximumAttempts", 5):
        value.update(state="retry", availableAt=(now + timedelta(seconds=min(3600, 2 ** value["attempts"] * 5))).isoformat())
    else:
        value["state"] = "dead_letter"
    return value


def schedule_due(schedule: dict[str, Any], *, now: datetime, running: bool) -> dict[str, Any]:
    if now.tzinfo is None:
        raise RuntimeGovernanceError("schedule:time_invalid")
    try:
        ZoneInfo(schedule["timezone"])
    except (KeyError, ZoneInfoNotFoundError) as exc:
        raise RuntimeGovernanceError("schedule:timezone_invalid") from exc
    due = datetime.fromisoformat(schedule["nextRunAt"]) <= now
    if not due or not schedule.get("enabled", True):
        return {"action": "none", "lateSeconds": 0}
    if running and schedule.get("overlapPolicy") == "forbid":
        return {"action": "defer", "lateSeconds": int((now - datetime.fromisoformat(schedule["nextRunAt"])).total_seconds())}
    return {"action": "enqueue_once", "lateSeconds": max(0, int((now - datetime.fromisoformat(schedule["nextRunAt"])).total_seconds()))}


def notification_policy(*, family: str, preference: str, quiet: bool) -> str:
    if family == "security":
        return "immediate"
    if preference not in {"immediate", "digest", "disabled"}:
        raise RuntimeGovernanceError("notification:preference_invalid")
    if preference == "immediate" and quiet:
        return "digest"
    return preference


def break_glass_status(grant: dict[str, Any], *, now: datetime) -> str:
    if now.tzinfo is None or grant.get("requesterRef") == grant.get("approverRef"):
        raise RuntimeGovernanceError("break_glass:invalid")
    if grant.get("revokedAt"):
        return "revoked"
    if now >= datetime.fromisoformat(grant["expiresAt"]):
        return "expired_review_required" if not grant.get("reviewedAt") else "expired_reviewed"
    return "active"
