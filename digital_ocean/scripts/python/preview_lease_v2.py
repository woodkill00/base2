#!/usr/bin/env python3
"""Atomic exact-identity lifecycle for a guarded full preview."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol


RUN_ID = re.compile(r"^[a-z0-9][a-z0-9-]{7,80}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STATES = {
    "prepared", "compute-bound", "dns-bound", "deploying", "live-verified",
    "teardown-requested", "compute-delete-pending", "dns-cleanup-pending", "destroyed", "blocked",
}
FIELDS = {
    "schemaVersion", "runId", "state", "armedAt", "expiresAt", "sourceCommit",
    "sourceArchiveSha256", "profileId", "profileDigest", "droplet", "dnsRecords",
    "ownerAdmissionDigest", "certificateMode", "budgetCeilingUsd", "lastError", "mutationCounts",
}
DROPLET_FIELDS = {"id", "name", "tags", "size", "createdAt"}
DNS_FIELDS = {"id", "domain", "type", "name", "value", "state"}


class LeaseV2ValidationError(ValueError): pass
class LeaseV2IntegrityError(RuntimeError): pass
class LeaseV2Conflict(RuntimeError): pass
class TeardownNotDue(LeaseV2Conflict): pass


class Provider(Protocol):
    def get_droplet(self, resource_id: str) -> dict | None: ...
    def delete_droplet(self, resource_id: str) -> None: ...
    def list_owned_droplets(self, run_id: str) -> list[dict]: ...
    def get_dns_record(self, domain: str, record_id: str) -> dict | None: ...
    def delete_dns_record(self, domain: str, record_id: str) -> None: ...


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _digest(value: dict) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise LeaseV2ValidationError("timestamp is invalid") from exc
    if result.tzinfo is None:
        raise LeaseV2ValidationError("timestamp requires timezone")
    return result.astimezone(UTC)


def validate_lease(value: Any) -> dict:
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise LeaseV2ValidationError("lease fields differ from schema")
    if value["schemaVersion"] != 2 or not RUN_ID.fullmatch(str(value["runId"])):
        raise LeaseV2ValidationError("lease identity is invalid")
    if value["state"] not in STATES:
        raise LeaseV2ValidationError("lease state is invalid")
    if _time(value["expiresAt"]) <= _time(value["armedAt"]):
        raise LeaseV2ValidationError("lease expiry is invalid")
    if not HEX40.fullmatch(str(value["sourceCommit"])):
        raise LeaseV2ValidationError("source commit is invalid")
    for field in ("sourceArchiveSha256", "profileDigest", "ownerAdmissionDigest"):
        if not HEX64.fullmatch(str(value[field])):
            raise LeaseV2ValidationError(f"{field} is invalid")
    if value["profileId"] != "base2-obsidian":
        raise LeaseV2ValidationError("profile identity is invalid")
    if value["certificateMode"] != "letsencrypt-staging-only":
        raise LeaseV2ValidationError("certificate mode is invalid")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,4})?", str(value["budgetCeilingUsd"])):
        raise LeaseV2ValidationError("budget ceiling is invalid")
    if value["lastError"] is not None and not isinstance(value["lastError"], str):
        raise LeaseV2ValidationError("last error is invalid")
    if set(value["mutationCounts"]) != {"dropletsDeleted", "dnsRecordsDeleted"}:
        raise LeaseV2ValidationError("mutation counts are invalid")
    if any(not isinstance(count, int) or count < 0 for count in value["mutationCounts"].values()):
        raise LeaseV2ValidationError("mutation count is invalid")
    droplet = value["droplet"]
    if droplet is not None:
        if not isinstance(droplet, dict) or set(droplet) != DROPLET_FIELDS:
            raise LeaseV2ValidationError("droplet fields are invalid")
        if not all(isinstance(droplet[field], str) and droplet[field] for field in DROPLET_FIELDS - {"tags"}):
            raise LeaseV2ValidationError("droplet identity is invalid")
        if not isinstance(droplet["tags"], list) or value["runId"] not in droplet["tags"]:
            raise LeaseV2ValidationError("droplet ownership tags are invalid")
        if droplet["size"] != "s-2vcpu-2gb":
            raise LeaseV2ValidationError("droplet size is invalid")
        _time(droplet["createdAt"])
    records = value["dnsRecords"]
    if not isinstance(records, list) or len(records) > 8:
        raise LeaseV2ValidationError("DNS records are invalid")
    identities = set()
    for row in records:
        if not isinstance(row, dict) or set(row) != DNS_FIELDS or row["type"] != "A":
            raise LeaseV2ValidationError("DNS record fields are invalid")
        identity = (row["domain"], row["id"])
        if identity in identities:
            raise LeaseV2ValidationError("DNS record identity is duplicated")
        identities.add(identity)
        if row["state"] not in {"bound", "delete-pending", "absent"}:
            raise LeaseV2ValidationError("DNS record state is invalid")
    return value


class FullPreviewLeaseStore:
    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or not self.root.is_dir():
            raise LeaseV2IntegrityError("lease root is invalid")
        os.chmod(self.root, 0o700)
        self.lock_path = self.root / ".lock"

    def _path(self, run_id: str) -> Path:
        if not RUN_ID.fullmatch(str(run_id)):
            raise LeaseV2ValidationError("run ID is invalid")
        return self.root / f"{run_id}.json"

    @contextmanager
    def _lock(self):
        descriptor = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _load(self, run_id: str) -> dict:
        path = self._path(run_id)
        if path.is_symlink() or not path.is_file():
            raise LeaseV2IntegrityError("lease is unavailable")
        try:
            envelope = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise LeaseV2IntegrityError("lease is unreadable") from exc
        if not isinstance(envelope, dict) or set(envelope) != {"lease", "integritySha256"}:
            raise LeaseV2IntegrityError("lease envelope is invalid")
        if envelope["integritySha256"] != _digest(envelope["lease"]):
            raise LeaseV2IntegrityError("lease integrity mismatch")
        try:
            return validate_lease(envelope["lease"])
        except LeaseV2ValidationError as exc:
            raise LeaseV2IntegrityError("stored lease violates schema") from exc

    def load(self, run_id: str) -> dict:
        with self._lock():
            return json.loads(_canonical(self._load(run_id)))

    def _write(self, lease: dict) -> None:
        validate_lease(lease)
        envelope = {"lease": lease, "integritySha256": _digest(lease)}
        descriptor, temporary = tempfile.mkstemp(dir=self.root, prefix=".lease-", suffix=".tmp")
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(_canonical(envelope) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path(lease["runId"]))
            os.chmod(self._path(lease["runId"]), 0o600)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def create(self, lease: dict) -> dict:
        candidate = json.loads(_canonical(validate_lease(lease)))
        with self._lock():
            path = self._path(candidate["runId"])
            if path.exists():
                current = self._load(candidate["runId"])
                if current == candidate:
                    return current
                raise LeaseV2Conflict("run ID already identifies another lease")
            self._write(candidate)
        return candidate

    def replace(self, lease: dict) -> dict:
        candidate = json.loads(_canonical(validate_lease(lease)))
        with self._lock():
            self._load(candidate["runId"])
            self._write(candidate)
        return candidate


def _droplet_equal(expected: dict, actual: dict) -> bool:
    return all(
        (sorted(actual.get(field, [])) == sorted(expected[field]) if field == "tags" else str(actual.get(field, "")) == str(expected[field]))
        for field in DROPLET_FIELDS
    )


def _dns_equal(expected: dict, actual: dict) -> bool:
    return all(str(actual.get(field, "")) == str(expected[field]) for field in ("id", "domain", "type", "name", "value"))


def teardown_full_preview(store: FullPreviewLeaseStore, provider: Provider, run_id: str, *, now: datetime, early_approved: bool = False) -> dict:
    lease = store.load(run_id)
    if lease["state"] == "destroyed":
        return lease
    if now.astimezone(UTC) < _time(lease["expiresAt"]) and not early_approved and lease["state"] != "dns-cleanup-pending":
        raise TeardownNotDue("preview is not expired and exact early teardown is not approved")
    droplet = lease["droplet"]
    if droplet and lease["state"] != "dns-cleanup-pending":
        current = provider.get_droplet(droplet["id"])
        if current is not None and not _droplet_equal(droplet, current):
            raise LeaseV2Conflict("droplet identity changed")
        lease["state"] = "compute-delete-pending"
        store.replace(lease)
        if current is not None:
            provider.delete_droplet(droplet["id"])
            lease["mutationCounts"]["dropletsDeleted"] += 1
        if provider.list_owned_droplets(run_id):
            lease["state"] = "blocked"
            lease["lastError"] = "owned droplets remain"
            store.replace(lease)
            raise LeaseV2Conflict("owned droplets remain after delete")
    lease["state"] = "dns-cleanup-pending"
    store.replace(lease)
    try:
        for row in lease["dnsRecords"]:
            if row["state"] == "absent":
                continue
            current = provider.get_dns_record(row["domain"], row["id"])
            if current is not None and not _dns_equal(row, current):
                raise LeaseV2Conflict("DNS identity changed")
            if current is not None:
                provider.delete_dns_record(row["domain"], row["id"])
                lease["mutationCounts"]["dnsRecordsDeleted"] += 1
            row["state"] = "absent"
            store.replace(lease)
    except Exception as exc:
        lease["state"] = "dns-cleanup-pending"
        lease["lastError"] = type(exc).__name__
        store.replace(lease)
        raise
    lease["state"] = "destroyed"
    lease["lastError"] = None
    return store.replace(lease)
