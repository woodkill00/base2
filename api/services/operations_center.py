"""Pure, bounded state contracts for the Base2 native operations center."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

HealthState = Literal[
    "healthy", "degraded", "unavailable", "stale", "unknown", "muted", "disabled"
]
SEVERITIES = {"info", "warning", "high", "critical"}
JOURNEYS = {
    "anonymous.public_page",
    "member.login",
    "member.navigation",
    "editor.content_preview",
    "administrator.operations_read",
    "member.form_submit",
    "editor.media_upload",
    "member.search",
    "member.logout",
}
SECRET_KEY = re.compile(
    r"token|password|secret|credential|authorization|cookie|private.?key|body|content",
    re.I,
)
CODE = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")


class OperationsContractError(ValueError):
    pass


def canonical_dimensions(value: Any) -> dict[str, str | int | float | bool]:
    if not isinstance(value, dict) or len(value) > 16:
        raise OperationsContractError("operations:dimensions_invalid")
    result: dict[str, str | int | float | bool] = {}
    for key in sorted(value):
        item = value[key]
        if (
            not isinstance(key, str)
            or not CODE.fullmatch(key)
            or SECRET_KEY.search(key)
            or not isinstance(item, str | int | float | bool)
            or isinstance(item, str)
            and len(item) > 200
        ):
            raise OperationsContractError("operations:dimensions_invalid")
        result[key] = item
    return result


def classify_health(
    *,
    enabled: bool,
    muted: bool,
    probe_state: str | None,
    observed_at: datetime | None,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> HealthState:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise OperationsContractError("operations:timezone_required")
    if not enabled:
        return "disabled"
    if muted:
        return "muted"
    if observed_at is None or expires_at is None or probe_state is None:
        return "unknown"
    if observed_at.tzinfo is None or expires_at.tzinfo is None or expires_at <= observed_at:
        raise OperationsContractError("operations:sample_time_invalid")
    if current > expires_at:
        return "stale"
    if probe_state not in {"healthy", "degraded", "unavailable"}:
        raise OperationsContractError("operations:probe_state_invalid")
    return probe_state  # type: ignore[return-value]


def synthetic_result(
    *, journey: str, role: str, source_commit: str, steps: list[dict[str, Any]]
) -> dict[str, Any]:
    if journey not in JOURNEYS or role not in {"anonymous", "member", "editor", "administrator"}:
        raise OperationsContractError("operations:journey_invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit or ""):
        raise OperationsContractError("operations:source_invalid")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
        raise OperationsContractError("operations:steps_invalid")
    normalized = []
    for step in steps:
        if not isinstance(step, dict) or set(step) != {"code", "passed", "durationMs"}:
            raise OperationsContractError("operations:step_invalid")
        if (
            not CODE.fullmatch(str(step["code"]))
            or type(step["passed"]) is not bool
            or type(step["durationMs"]) is not int
            or not 0 <= step["durationMs"] <= 30_000
        ):
            raise OperationsContractError("operations:step_invalid")
        normalized.append(
            {
                "code": step["code"],
                "passed": step["passed"],
                "durationMs": step["durationMs"],
            }
        )
    payload = {
        "journey": journey,
        "role": role,
        "sourceCommit": source_commit,
        "status": "passed" if all(step["passed"] for step in normalized) else "failed",
        "steps": normalized,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["resultDigest"] = hashlib.sha256(canonical).hexdigest()
    return payload


def incident_fingerprint(*, site_id: str, service_key: str, code: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,62}", site_id or ""):
        raise OperationsContractError("operations:site_invalid")
    if not CODE.fullmatch(service_key or "") or not CODE.fullmatch(code or ""):
        raise OperationsContractError("operations:incident_invalid")
    return hashlib.sha256(f"{site_id}\0{service_key}\0{code}".encode()).hexdigest()


def next_incident_state(*, prior: str | None, failing: bool, acknowledged: bool = False) -> str:
    if prior not in {None, "firing", "acknowledged", "resolved", "recurring"}:
        raise OperationsContractError("operations:incident_state_invalid")
    if not failing:
        return "resolved"
    if prior == "resolved":
        return "recurring"
    if acknowledged:
        return "acknowledged"
    return prior or "firing"


def alert_schedule(
    *,
    severity: str,
    attempts: int,
    maximum_attempts: int,
    now: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    if severity not in SEVERITIES:
        raise OperationsContractError("operations:severity_invalid")
    if (
        type(attempts) is not int
        or type(maximum_attempts) is not int
        or not 0 <= attempts <= maximum_attempts <= 10
    ):
        raise OperationsContractError("operations:attempt_invalid")
    if now.tzinfo is None or expires_at.tzinfo is None:
        raise OperationsContractError("operations:timezone_required")
    if now >= expires_at:
        return {"status": "expired", "nextAttemptAt": None}
    if attempts >= maximum_attempts:
        return {"status": "failed", "nextAttemptAt": None}
    delay = min(900, 15 * (2**attempts))
    due = min(now + timedelta(seconds=delay), expires_at)
    return {"status": "queued", "nextAttemptAt": due.isoformat()}


def objective_state(*, successful: int, total: int, target: float, warning: float) -> str:
    if (
        type(successful) is not int
        or type(total) is not int
        or not 0 <= successful <= total
        or total <= 0
        or not 0 <= warning <= target <= 1
    ):
        raise OperationsContractError("operations:objective_invalid")
    ratio = successful / total
    if ratio >= target:
        return "met"
    if ratio >= warning:
        return "at_risk"
    return "breached"
