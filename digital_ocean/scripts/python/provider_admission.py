#!/usr/bin/env python3
"""Durable provider admission, bounded retry, and circuit breaking."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SAFE_SCOPE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
STATES = {"closed", "open", "half_open"}


class AdmissionDenied(RuntimeError):
    """A safe precondition or open circuit denied a provider operation."""


class CircuitIntegrityError(RuntimeError):
    """Durable circuit state is unavailable, malformed, or modified."""


@dataclass(frozen=True)
class AdmissionPolicy:
    maximum_active_resources: int = 1
    minimum_disk_free_bytes: int = 1
    minimum_memory_available_bytes: int = 1
    maximum_attempts: int = 3
    open_after_failures: int = 2
    cooldown: timedelta = timedelta(minutes=5)
    retry_delays: tuple[float, ...] = (1.0, 2.0)

    def __post_init__(self) -> None:
        integer_fields = (
            self.maximum_active_resources,
            self.minimum_disk_free_bytes,
            self.minimum_memory_available_bytes,
            self.maximum_attempts,
            self.open_after_failures,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1
            for value in integer_fields
        ):
            raise ValueError("admission policy limits must be positive integers")
        if self.cooldown <= timedelta(0):
            raise ValueError("circuit cooldown must be positive")
        if len(self.retry_delays) < self.maximum_attempts - 1 or any(
            not isinstance(delay, int | float) or delay < 0 for delay in self.retry_delays
        ):
            raise ValueError("retry delay policy is invalid")


@dataclass(frozen=True)
class AdmissionSnapshot:
    active_resources: int
    provider_quota: int
    projected_minor_units: int
    budget_ceiling_minor_units: int
    disk_free_bytes: int
    memory_available_bytes: int
    oom_kills: int

    def __post_init__(self) -> None:
        for value in self.__dict__.values():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("admission snapshot values must be non-negative integers")
        if self.provider_quota < 1:
            raise ValueError("provider quota must be positive")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _format(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse(value: Any) -> datetime:
    if not isinstance(value, str):
        raise CircuitIntegrityError("circuit timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CircuitIntegrityError("circuit timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise CircuitIntegrityError("circuit timestamp lacks timezone")
    return parsed.astimezone(UTC)


def _validate_state(value: Any, scope: str) -> dict[str, Any]:
    fields = {
        "schemaVersion",
        "scope",
        "state",
        "consecutiveFailures",
        "openedAt",
        "notificationCodes",
        "pendingNotifications",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise CircuitIntegrityError("circuit state contract is invalid")
    if value["schemaVersion"] != 1 or value["scope"] != scope or value["state"] not in STATES:
        raise CircuitIntegrityError("circuit identity or state is invalid")
    failures = value["consecutiveFailures"]
    if isinstance(failures, bool) or not isinstance(failures, int) or failures < 0:
        raise CircuitIntegrityError("circuit failure count is invalid")
    opened = value["openedAt"]
    if value["state"] == "closed" and opened is not None:
        raise CircuitIntegrityError("closed circuit cannot have openedAt")
    if value["state"] != "closed":
        _parse(opened)
    codes = value["notificationCodes"]
    if (
        not isinstance(codes, list)
        or len(codes) != len(set(codes))
        or not all(
            isinstance(item, str) and re.fullmatch(r"[a-z][a-z0-9_]{2,63}", item) for item in codes
        )
    ):
        raise CircuitIntegrityError("circuit notification state is invalid")
    pending = value["pendingNotifications"]
    if (
        not isinstance(pending, list)
        or len(pending) != len(set(pending))
        or not set(pending).issubset(codes)
    ):
        raise CircuitIntegrityError("pending notification state is invalid")
    return value


class ProviderAdmissionController:
    def __init__(
        self,
        root: str | os.PathLike[str],
        policy: AdmissionPolicy,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        notify: Callable[[dict[str, Any]], None] = lambda _receipt: None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.root = Path(root)
        self.policy = policy
        self.clock = clock
        self.notify = notify
        self.sleep = sleep
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or not self.root.is_dir():
            raise CircuitIntegrityError("circuit root must be a real directory")
        os.chmod(self.root, 0o700)
        self.lock_path = self.root / ".lock"

    def _path(self, scope: str) -> Path:
        if not isinstance(scope, str) or not SAFE_SCOPE.fullmatch(scope):
            raise ValueError("provider scope is unsafe")
        return self.root / f"{scope}.json"

    @contextmanager
    def _lock(self):
        descriptor = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _default(scope: str) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "scope": scope,
            "state": "closed",
            "consecutiveFailures": 0,
            "openedAt": None,
            "notificationCodes": [],
            "pendingNotifications": [],
        }

    def _load_unlocked(self, scope: str) -> dict[str, Any]:
        path = self._path(scope)
        if not path.exists():
            state = self._default(scope)
            self._write_unlocked(state)
            return state
        try:
            if path.is_symlink() or not path.is_file():
                raise CircuitIntegrityError("circuit state is unavailable")
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CircuitIntegrityError("circuit state is unavailable") from exc
        if not isinstance(envelope, dict) or set(envelope) != {"state", "integrityDigest"}:
            raise CircuitIntegrityError("circuit envelope is invalid")
        state = envelope["state"]
        if envelope["integrityDigest"] != _digest(state):
            raise CircuitIntegrityError("circuit digest verification failed")
        return _validate_state(state, scope)

    def _write_unlocked(self, state: dict[str, Any]) -> None:
        _validate_state(state, state["scope"])
        envelope = {"state": state, "integrityDigest": _digest(state)}
        descriptor, name = tempfile.mkstemp(prefix=".circuit.", suffix=".tmp", dir=self.root)
        temporary = Path(name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(_canonical(envelope) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            target = self._path(state["scope"])
            os.replace(temporary, target)
            os.chmod(target, 0o600)
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    def status(self, scope: str) -> dict[str, Any]:
        with self._lock():
            return json.loads(_canonical(self._load_unlocked(scope)))

    def _emit_once(self, state: dict[str, Any], code: str) -> dict[str, Any] | None:
        if code in state["notificationCodes"]:
            return None
        state["notificationCodes"].append(code)
        state["pendingNotifications"].append(code)
        self._write_unlocked(state)
        return {"schemaVersion": 1, "code": code, "scope": state["scope"]}

    def _deliver(self, receipt: dict[str, Any]) -> None:
        try:
            self.notify(receipt)
        except Exception:
            return
        with self._lock():
            state = self._load_unlocked(receipt["scope"])
            if receipt["code"] in state["pendingNotifications"]:
                state["pendingNotifications"].remove(receipt["code"])
                self._write_unlocked(state)

    def _flush_pending(self, scope: str) -> None:
        with self._lock():
            pending = list(self._load_unlocked(scope)["pendingNotifications"])
        for code in pending:
            self._deliver({"schemaVersion": 1, "code": code, "scope": scope})

    def _deny_code(self, snapshot: AdmissionSnapshot) -> str | None:
        if snapshot.active_resources >= snapshot.provider_quota:
            return "provider_quota"
        if snapshot.active_resources >= self.policy.maximum_active_resources:
            return "resource_limit"
        if snapshot.projected_minor_units > snapshot.budget_ceiling_minor_units:
            return "budget_ceiling"
        if snapshot.disk_free_bytes < self.policy.minimum_disk_free_bytes:
            return "disk_pressure"
        if snapshot.memory_available_bytes < self.policy.minimum_memory_available_bytes:
            return "memory_pressure"
        if snapshot.oom_kills > 0:
            return "oom_detected"
        return None

    def execute(self, scope: str, snapshot: AdmissionSnapshot, operation: Callable[[], Any]) -> Any:
        if not isinstance(snapshot, AdmissionSnapshot):
            raise ValueError("admission snapshot is required")
        self._flush_pending(scope)
        now = self.clock().astimezone(UTC)
        notices: list[dict[str, Any]] = []
        with self._lock():
            state = self._load_unlocked(scope)
            deny_code = self._deny_code(snapshot)
            if deny_code is not None:
                notice = self._emit_once(state, f"admission_{deny_code}")
                if notice:
                    notices.append(notice)
                denied = deny_code
            else:
                denied = None
                state["notificationCodes"] = [
                    item for item in state["notificationCodes"] if not item.startswith("admission_")
                ]
                state["pendingNotifications"] = [
                    item
                    for item in state["pendingNotifications"]
                    if not item.startswith("admission_")
                ]
                if state["state"] == "open":
                    if now < _parse(state["openedAt"]) + self.policy.cooldown:
                        denied = "circuit_open"
                    else:
                        state["state"] = "half_open"
                elif state["state"] == "half_open":
                    denied = "circuit_open"
                self._write_unlocked(state)
        for notice in notices:
            self._deliver(notice)
        if denied is not None:
            raise AdmissionDenied(denied)

        last_error: Exception | None = None
        for attempt in range(1, self.policy.maximum_attempts + 1):
            try:
                result = operation()
            except Exception as exc:
                last_error = exc
                status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
                retryable = status == 429 or (isinstance(status, int) and 500 <= status <= 599)
                if not retryable or attempt == self.policy.maximum_attempts:
                    break
                self.sleep(self.policy.retry_delays[attempt - 1])
            else:
                recovery_notice = None
                with self._lock():
                    state = self._load_unlocked(scope)
                    was_open = state["state"] in {"open", "half_open"}
                    state.update(state="closed", consecutiveFailures=0, openedAt=None)
                    state["notificationCodes"] = [
                        item
                        for item in state["notificationCodes"]
                        if item not in {"provider_circuit_open", "provider_circuit_recovered"}
                    ]
                    state["pendingNotifications"] = [
                        item
                        for item in state["pendingNotifications"]
                        if item not in {"provider_circuit_open", "provider_circuit_recovered"}
                    ]
                    if was_open:
                        recovery_notice = self._emit_once(state, "provider_circuit_recovered")
                    else:
                        self._write_unlocked(state)
                if recovery_notice:
                    self._deliver(recovery_notice)
                return result

        assert last_error is not None
        notice = None
        with self._lock():
            state = self._load_unlocked(scope)
            state["consecutiveFailures"] += attempt
            if state["consecutiveFailures"] >= self.policy.open_after_failures:
                state.update(state="open", openedAt=_format(now))
                state["notificationCodes"] = [
                    item
                    for item in state["notificationCodes"]
                    if item != "provider_circuit_recovered"
                ]
                state["pendingNotifications"] = [
                    item
                    for item in state["pendingNotifications"]
                    if item != "provider_circuit_recovered"
                ]
                notice = self._emit_once(state, "provider_circuit_open")
            else:
                self._write_unlocked(state)
        if notice:
            self._deliver(notice)
        raise last_error
