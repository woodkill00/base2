#!/usr/bin/env python3
"""Integrity-bound, atomic state store for temporary preview resources."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

LEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{6,126}[A-Za-z0-9]$")
SITE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CURRENCY = re.compile(r"^[A-Z]{3}$")
STATES = {
    "planned",
    "provisioning",
    "bootstrapping",
    "healthy",
    "observing",
    "teardown_due",
    "destroying",
    "destroyed",
    "failed",
}
TRANSITIONS = {
    "planned": {"provisioning", "teardown_due", "failed"},
    "provisioning": {"bootstrapping", "teardown_due", "failed"},
    "bootstrapping": {"healthy", "teardown_due", "failed"},
    "healthy": {"observing", "teardown_due", "failed"},
    "observing": {"teardown_due", "failed"},
    "teardown_due": {"destroying", "failed"},
    "destroying": {"destroyed", "failed"},
    "destroyed": set(),
    "failed": {"teardown_due"},
}
TERMINAL_STATES = {"destroyed"}
LEASE_FIELDS = {
    "schemaVersion",
    "leaseId",
    "siteId",
    "sourceCommit",
    "manifestDigest",
    "owner",
    "state",
    "createdAt",
    "expiresAt",
    "costPolicy",
    "resources",
    "dnsMutations",
}
LEASE_OPTIONAL_FIELDS = {"lastActivityAt", "idleExpiresAt"}
RESOURCE_FIELDS = {"provider", "kind", "providerId", "ownershipTag"}
DNS_FIELDS = {"zone", "name", "type", "previousValues", "desiredValues", "state"}
DNS_STATES = {"planned", "applied", "verified", "restored"}


class LeaseError(RuntimeError):
    """Base error for lease state operations."""


class LeaseValidationError(LeaseError):
    """Lease input does not match the reviewed contract."""


class LeaseIntegrityError(LeaseError):
    """Stored lease state is corrupt or has been modified."""


class LeaseConflict(LeaseError):
    """Requested operation conflicts with durable lease state."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _digest(lease: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(lease)).hexdigest()


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise LeaseValidationError(f"{field} must be a date-time string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LeaseValidationError(f"{field} must be a valid date-time") from exc
    if parsed.tzinfo is None:
        raise LeaseValidationError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def ownership_tag(lease_id: str, site_id: str, manifest_digest: str) -> str:
    if not LEASE_ID.fullmatch(lease_id):
        raise LeaseValidationError("leaseId has an unsafe format")
    if not SITE_ID.fullmatch(site_id):
        raise LeaseValidationError("siteId has an unsafe format")
    if not HEX64.fullmatch(manifest_digest):
        raise LeaseValidationError("manifestDigest must be a SHA-256 digest")
    return f"base2-preview:{lease_id}:{site_id}:{manifest_digest[:16]}"


def _require_exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise LeaseValidationError(f"{label} has unknown field: {unknown[0]}")
    if missing:
        raise LeaseValidationError(f"{label} is missing field: {missing[0]}")


def validate_lease(lease: Any) -> dict[str, Any]:
    if not isinstance(lease, dict):
        raise LeaseValidationError("lease must be an object")
    unknown = sorted(set(lease) - LEASE_FIELDS - LEASE_OPTIONAL_FIELDS)
    missing = sorted(LEASE_FIELDS - set(lease))
    if unknown:
        raise LeaseValidationError(f"lease has unknown field: {unknown[0]}")
    if missing:
        raise LeaseValidationError(f"lease is missing field: {missing[0]}")
    if lease["schemaVersion"] != 1:
        raise LeaseValidationError("schemaVersion must be 1")
    if not isinstance(lease["leaseId"], str) or not LEASE_ID.fullmatch(lease["leaseId"]):
        raise LeaseValidationError("leaseId has an unsafe format")
    if not isinstance(lease["siteId"], str) or not SITE_ID.fullmatch(lease["siteId"]):
        raise LeaseValidationError("siteId has an unsafe format")
    if not isinstance(lease["sourceCommit"], str) or not HEX40.fullmatch(lease["sourceCommit"]):
        raise LeaseValidationError("sourceCommit must be a full commit digest")
    if not isinstance(lease["manifestDigest"], str) or not HEX64.fullmatch(lease["manifestDigest"]):
        raise LeaseValidationError("manifestDigest must be a SHA-256 digest")
    if not isinstance(lease["owner"], str) or not lease["owner"].strip():
        raise LeaseValidationError("owner must be non-empty")
    if lease["state"] not in STATES:
        raise LeaseValidationError("state is invalid")
    created = _timestamp(lease["createdAt"], "createdAt")
    expires = _timestamp(lease["expiresAt"], "expiresAt")
    if expires <= created:
        raise LeaseValidationError("expiresAt must be after createdAt")
    activity_fields = LEASE_OPTIONAL_FIELDS & set(lease)
    if activity_fields and activity_fields != LEASE_OPTIONAL_FIELDS:
        raise LeaseValidationError("idle activity fields must be supplied together")
    if activity_fields:
        last_activity = _timestamp(lease["lastActivityAt"], "lastActivityAt")
        idle_expires = _timestamp(lease["idleExpiresAt"], "idleExpiresAt")
        if last_activity < created or idle_expires <= last_activity:
            raise LeaseValidationError("idle activity window is invalid")

    cost = lease["costPolicy"]
    if not isinstance(cost, dict):
        raise LeaseValidationError("costPolicy must be an object")
    _require_exact_fields(cost, {"currency", "maximumMinorUnits"}, "costPolicy")
    if not isinstance(cost["currency"], str) or not CURRENCY.fullmatch(cost["currency"]):
        raise LeaseValidationError("costPolicy currency is invalid")
    if (
        not isinstance(cost["maximumMinorUnits"], int)
        or isinstance(cost["maximumMinorUnits"], bool)
        or cost["maximumMinorUnits"] < 0
    ):
        raise LeaseValidationError("costPolicy maximumMinorUnits is invalid")

    resources = lease["resources"]
    if not isinstance(resources, list):
        raise LeaseValidationError("resources must be an array")
    expected_tag = ownership_tag(lease["leaseId"], lease["siteId"], lease["manifestDigest"])
    resource_keys: set[tuple[str, str, str]] = set()
    for resource in resources:
        if not isinstance(resource, dict):
            raise LeaseValidationError("resource must be an object")
        _require_exact_fields(resource, RESOURCE_FIELDS, "resource")
        for field in ("provider", "kind", "providerId", "ownershipTag"):
            if not isinstance(resource[field], str) or not resource[field]:
                raise LeaseValidationError(f"resource {field} must be non-empty")
        if resource["ownershipTag"] != expected_tag:
            raise LeaseValidationError("resource ownershipTag is not exact")
        key = (resource["provider"], resource["kind"], resource["providerId"])
        if key in resource_keys:
            raise LeaseValidationError("resource identity is duplicated")
        resource_keys.add(key)

    mutations = lease["dnsMutations"]
    if not isinstance(mutations, list):
        raise LeaseValidationError("dnsMutations must be an array")
    for mutation in mutations:
        if not isinstance(mutation, dict):
            raise LeaseValidationError("DNS mutation must be an object")
        _require_exact_fields(mutation, DNS_FIELDS, "DNS mutation")
        if mutation["state"] not in DNS_STATES:
            raise LeaseValidationError("DNS mutation state is invalid")
        for field in ("zone", "name", "type"):
            if not isinstance(mutation[field], str) or not mutation[field]:
                raise LeaseValidationError(f"DNS mutation {field} must be non-empty")
        for field in ("previousValues", "desiredValues"):
            values = mutation[field]
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise LeaseValidationError(f"DNS mutation {field} must be a text array")
    return lease


class LeaseStore:
    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        maximum_renewal: timedelta = timedelta(hours=24),
    ) -> None:
        if maximum_renewal <= timedelta(0):
            raise LeaseValidationError("maximum renewal must be positive")
        self.root = Path(root)
        self.maximum_renewal = maximum_renewal
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or not self.root.is_dir():
            raise LeaseIntegrityError("lease root must be a real directory")
        os.chmod(self.root, 0o700)
        self._lock_path = self.root / ".lock"

    def _path(self, lease_id: str) -> Path:
        if not isinstance(lease_id, str) or not LEASE_ID.fullmatch(lease_id):
            raise LeaseValidationError("leaseId has an unsafe format")
        return self.root / f"{lease_id}.json"

    @contextmanager
    def _lock(self):
        descriptor = os.open(self._lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _load_unlocked(self, lease_id: str) -> dict[str, Any]:
        path = self._path(lease_id)
        try:
            if path.is_symlink() or not path.is_file():
                raise LeaseIntegrityError("lease state is unavailable")
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LeaseIntegrityError("lease state is not valid JSON") from exc
        except OSError as exc:
            raise LeaseIntegrityError("lease state is unavailable") from exc
        if not isinstance(envelope, dict) or set(envelope) != {"lease", "integrityDigest"}:
            raise LeaseIntegrityError("lease envelope is invalid")
        lease = envelope["lease"]
        digest = envelope["integrityDigest"]
        if not isinstance(lease, dict) or not isinstance(digest, str) or _digest(lease) != digest:
            raise LeaseIntegrityError("lease digest verification failed")
        try:
            return validate_lease(lease)
        except LeaseValidationError as exc:
            raise LeaseIntegrityError("stored lease violates its contract") from exc

    def load(self, lease_id: str) -> dict[str, Any]:
        with self._lock():
            return self._load_unlocked(lease_id)

    def exists(self, lease_id: str) -> bool:
        """Return whether an exact lease path exists without hiding corruption."""
        with self._lock():
            path = self._path(lease_id)
            if path.is_symlink():
                raise LeaseIntegrityError("lease state must not be a symbolic link")
            return path.exists()

    def _write_unlocked(self, lease: dict[str, Any]) -> None:
        validate_lease(lease)
        target = self._path(lease["leaseId"])
        envelope = {"lease": lease, "integrityDigest": _digest(lease)}
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{lease['leaseId']}.", suffix=".tmp", dir=self.root
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                handle.write(_canonical(envelope) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            os.chmod(target, 0o600)
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    def create(self, lease: dict[str, Any]) -> dict[str, Any]:
        validate_lease(lease)
        candidate = json.loads(_canonical(lease))
        with self._lock():
            path = self._path(candidate["leaseId"])
            if path.exists() or path.is_symlink():
                current = self._load_unlocked(candidate["leaseId"])
                if current == candidate:
                    return current
                raise LeaseConflict("leaseId already identifies a different lease")
            self._write_unlocked(candidate)
            return candidate

    def transition(self, lease_id: str, target_state: str) -> dict[str, Any]:
        if target_state not in STATES:
            raise LeaseValidationError("target state is invalid")
        with self._lock():
            lease = self._load_unlocked(lease_id)
            current = lease["state"]
            if current == target_state:
                return lease
            if target_state not in TRANSITIONS[current]:
                raise LeaseConflict(f"state transition {current} -> {target_state} is not allowed")
            updated = {**lease, "state": target_state}
            self._write_unlocked(updated)
            return updated

    def add_resource(self, lease_id: str, resource: dict[str, str]) -> dict[str, Any]:
        with self._lock():
            lease = self._load_unlocked(lease_id)
            candidate = json.loads(_canonical(lease))
            if resource in candidate["resources"]:
                return lease
            if lease["state"] not in {"planned", "provisioning"}:
                raise LeaseConflict("resources can only be admitted while provisioning")
            candidate["resources"].append(resource)
            validate_lease(candidate)
            self._write_unlocked(candidate)
            return candidate

    def bind_dns_desired_values(self, lease_id: str, values: list[str]) -> dict[str, Any]:
        if not isinstance(values, list) or not values or not all(
            isinstance(item, str) and item for item in values
        ):
            raise LeaseValidationError("DNS desired values must be a non-empty text array")
        if len(values) != len(set(values)):
            raise LeaseValidationError("DNS desired values are duplicated")
        with self._lock():
            lease = self._load_unlocked(lease_id)
            if lease["state"] != "provisioning":
                raise LeaseConflict("DNS desired values bind only while provisioning")
            candidate = json.loads(_canonical(lease))
            if not candidate["dnsMutations"]:
                raise LeaseConflict("lease has no DNS mutation to bind")
            current_sets = [mutation["desiredValues"] for mutation in candidate["dnsMutations"]]
            if all(current == values for current in current_sets):
                return lease
            if any(current for current in current_sets):
                raise LeaseConflict("DNS desired values already differ from provider identity")
            for mutation in candidate["dnsMutations"]:
                if mutation["state"] != "planned":
                    raise LeaseConflict("DNS desired values cannot bind after mutation")
                mutation["desiredValues"] = list(values)
            validate_lease(candidate)
            self._write_unlocked(candidate)
            return candidate

    def renew(
        self,
        lease_id: str,
        extension: timedelta,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if extension <= timedelta(0) or extension > self.maximum_renewal:
            raise LeaseValidationError("renewal limit exceeded")
        current_time = (now or datetime.now(UTC)).astimezone(UTC)
        with self._lock():
            lease = self._load_unlocked(lease_id)
            if lease["state"] in TERMINAL_STATES:
                raise LeaseConflict("terminal lease cannot be renewed")
            expires = _timestamp(lease["expiresAt"], "expiresAt")
            base = max(expires, current_time)
            updated = {**lease, "expiresAt": _format_timestamp(base + extension)}
            self._write_unlocked(updated)
            return updated

    def update_dns_state(self, lease_id: str, index: int, target_state: str) -> dict[str, Any]:
        allowed = {
            "planned": {"applied", "restored"},
            "applied": {"verified", "restored"},
            "verified": {"restored"},
            "restored": set(),
        }
        if target_state not in DNS_STATES:
            raise LeaseValidationError("DNS mutation target state is invalid")
        with self._lock():
            lease = self._load_unlocked(lease_id)
            mutations = lease["dnsMutations"]
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(mutations)
            ):
                raise LeaseValidationError("DNS mutation index is invalid")
            current = mutations[index]["state"]
            if current == target_state:
                return lease
            if target_state not in allowed[current]:
                raise LeaseConflict(
                    f"DNS mutation transition {current} -> {target_state} is not allowed"
                )
            updated = json.loads(_canonical(lease))
            updated["dnsMutations"][index]["state"] = target_state
            self._write_unlocked(updated)
            return updated

    def touch_activity(
        self,
        lease_id: str,
        *,
        now: datetime,
        idle_timeout: timedelta,
    ) -> dict[str, Any]:
        if idle_timeout <= timedelta(0):
            raise LeaseValidationError("idle timeout must be positive")
        current_time = now.astimezone(UTC)
        with self._lock():
            lease = self._load_unlocked(lease_id)
            if lease["state"] in TERMINAL_STATES:
                raise LeaseConflict("terminal lease activity cannot be updated")
            updated = {
                **lease,
                "lastActivityAt": _format_timestamp(current_time),
                "idleExpiresAt": _format_timestamp(current_time + idle_timeout),
            }
            self._write_unlocked(updated)
            return updated

    def reconcile_expired(self, *, now: datetime | None = None) -> list[str]:
        current_time = (now or datetime.now(UTC)).astimezone(UTC)
        reconciled: list[str] = []
        with self._lock():
            for path in sorted(self.root.glob("*.json")):
                lease_id = path.stem
                lease = self._load_unlocked(lease_id)
                if lease["state"] in {"teardown_due", "destroying", "destroyed"}:
                    continue
                deadlines = [_timestamp(lease["expiresAt"], "expiresAt")]
                if "idleExpiresAt" in lease:
                    deadlines.append(_timestamp(lease["idleExpiresAt"], "idleExpiresAt"))
                if min(deadlines) <= current_time:
                    updated = {**lease, "state": "teardown_due"}
                    self._write_unlocked(updated)
                    reconciled.append(lease_id)
        return reconciled
