#!/usr/bin/env python3
"""Provider-neutral, fail-closed immutable release lifecycle."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import re
import tempfile
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RELEASE_ID = re.compile(r"^release-[A-Za-z0-9._-]{4,120}$")
IMAGE = re.compile(r"^[a-z0-9][a-z0-9./_-]{2,190}@sha256:[0-9a-f]{64}$")
ENVIRONMENTS = {"development", "test", "preview", "staging", "production"}
ACTIONS = {"prepare", "stage", "canary", "promote", "rollback"}
STATES = {"empty", "prepared", "staged", "canary", "promoted", "halted", "rolled-back"}
RELEASE_FIELDS = {
    "schemaVersion",
    "releaseId",
    "sourceCommit",
    "sourceClean",
    "images",
    "migrationsDigest",
    "configurationSchemaVersion",
    "configurationDigest",
    "sbomDigest",
    "provenanceDigest",
    "artifactDigest",
    "createdAt",
    "signature",
}
APPROVAL_FIELDS = {
    "schemaVersion",
    "approvalId",
    "action",
    "releaseId",
    "environment",
    "expiresAt",
    "digest",
}


class ReleaseError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ReleaseError("release:time_invalid") from exc
    if result.tzinfo is None:
        raise ReleaseError("release:time_invalid")
    return result.astimezone(UTC)


def _unsigned_release(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in sorted(RELEASE_FIELDS - {"signature"})}


def sign_release(value: dict[str, Any], *, key: bytes) -> dict[str, Any]:
    if len(key) < 32:
        raise ReleaseError("release:key_invalid")
    candidate = dict(value)
    candidate["artifactDigest"] = _digest(
        {key: candidate[key] for key in sorted(RELEASE_FIELDS - {"artifactDigest", "signature"})}
    )
    candidate["signature"] = hmac.new(
        key, _canonical(_unsigned_release(candidate)), hashlib.sha256
    ).hexdigest()
    validate_release(candidate, key=key)
    return candidate


def validate_release(value: Any, *, key: bytes) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != RELEASE_FIELDS
        or value.get("schemaVersion") != 2
    ):
        raise ReleaseError("release:manifest_invalid")
    if not RELEASE_ID.fullmatch(str(value["releaseId"])) or not HEX40.fullmatch(
        str(value["sourceCommit"])
    ):
        raise ReleaseError("release:identity_invalid")
    if value["sourceClean"] is not True:
        raise ReleaseError("release:source_dirty")
    images = value["images"]
    if (
        not isinstance(images, dict)
        or not images
        or any(not IMAGE.fullmatch(str(item)) for item in images.values())
    ):
        raise ReleaseError("release:image_not_immutable")
    for field in (
        "migrationsDigest",
        "configurationDigest",
        "sbomDigest",
        "provenanceDigest",
        "artifactDigest",
        "signature",
    ):
        if not HEX64.fullmatch(str(value[field])):
            raise ReleaseError(f"release:{field}_invalid")
    if (
        type(value["configurationSchemaVersion"]) is not int
        or value["configurationSchemaVersion"] < 1
    ):
        raise ReleaseError("release:configuration_invalid")
    _time(value["createdAt"])
    expected_artifact = _digest(
        {key: value[key] for key in sorted(RELEASE_FIELDS - {"artifactDigest", "signature"})}
    )
    if not hmac.compare_digest(expected_artifact, value["artifactDigest"]):
        raise ReleaseError("release:artifact_changed")
    expected_signature = hmac.new(
        key, _canonical(_unsigned_release(value)), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, value["signature"]):
        raise ReleaseError("release:signature_invalid")
    return json.loads(json.dumps(value))


def approval(
    *,
    approval_id: str,
    action: str,
    release_id: str,
    environment: str,
    expires_at: str,
    key: bytes,
) -> dict[str, Any]:
    if len(key) < 32 or not re.fullmatch(r"approval-[A-Za-z0-9._-]{4,120}", approval_id or ""):
        raise ReleaseError("approval:identity_invalid")
    value = {
        "schemaVersion": 1,
        "approvalId": approval_id,
        "action": action,
        "releaseId": release_id,
        "environment": environment,
        "expiresAt": expires_at,
    }
    value["digest"] = hmac.new(key, _canonical(value), hashlib.sha256).hexdigest()
    return value


def validate_approval(
    value: Any,
    *,
    action: str,
    release_id: str,
    environment: str,
    now: datetime,
    key: bytes,
) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != APPROVAL_FIELDS
        or value.get("schemaVersion") != 1
    ):
        raise ReleaseError("approval:invalid")
    unsigned = {key: value[key] for key in APPROVAL_FIELDS - {"digest"}}
    expected = hmac.new(key, _canonical(unsigned), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(value["digest"]), expected):
        raise ReleaseError("approval:integrity_invalid")
    if (
        action not in ACTIONS
        or value["action"] != action
        or value["releaseId"] != release_id
        or value["environment"] != environment
    ):
        raise ReleaseError("approval:scope_mismatch")
    if now.tzinfo is None or now.astimezone(UTC) >= _time(value["expiresAt"]):
        raise ReleaseError("approval:expired")


class ReleaseJournal:
    def __init__(self, path: Path, *, key: bytes):
        self.path = path
        self.key = key
        self.lock = path.with_suffix(path.suffix + ".lock")

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.lock, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(descriptor)
            raise ReleaseError("release:concurrent_runner") from exc
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schemaVersion": 1,
                "state": "empty",
                "environment": None,
                "candidate": None,
                "current": None,
                "previous": None,
                "checkpoints": [],
                "receipts": [],
            }
        if self.path.is_symlink() or not self.path.is_file():
            raise ReleaseError("release:journal_unsafe")
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            raise ReleaseError("release:journal_invalid") from exc
        if (
            set(envelope) != {"journal", "integrity"}
            or envelope["integrity"]
            != hmac.new(self.key, _canonical(envelope["journal"]), hashlib.sha256).hexdigest()
        ):
            raise ReleaseError("release:journal_integrity")
        state = envelope["journal"]
        if not isinstance(state, dict) or state.get("state") not in STATES:
            raise ReleaseError("release:journal_invalid")
        return state

    def write(self, state: dict[str, Any]) -> None:
        envelope = {
            "journal": state,
            "integrity": hmac.new(self.key, _canonical(state), hashlib.sha256).hexdigest(),
        }
        descriptor, temporary = tempfile.mkstemp(prefix=".release-", dir=self.path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(_canonical(envelope) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
        finally:
            Path(temporary).unlink(missing_ok=True)


class ProductionReleaseController:
    def __init__(self, path: Path, *, release_key: bytes, approval_key: bytes):
        if len(release_key) < 32 or len(approval_key) < 32 or release_key == approval_key:
            raise ReleaseError("release:key_invalid")
        self.store = ReleaseJournal(path, key=release_key)
        self.release_key = release_key
        self.approval_key = approval_key

    def _receipt(self, state: dict[str, Any], action: str, status: str) -> dict[str, Any]:
        value = {
            "action": action,
            "status": status,
            "environment": state["environment"],
            "releaseId": state["candidate"]["releaseId"] if state["candidate"] else None,
            "checkpointCount": len(state["checkpoints"]),
        }
        value["digest"] = hmac.new(self.release_key, _canonical(value), hashlib.sha256).hexdigest()
        return value

    def transition(
        self,
        *,
        action: str,
        release: dict[str, Any],
        environment: str,
        owner_approval: dict[str, Any],
        now: datetime,
        health: Callable[[str], bool] = lambda _: True,
    ) -> dict[str, Any]:
        candidate = validate_release(release, key=self.release_key)
        if environment not in ENVIRONMENTS:
            raise ReleaseError("release:environment_invalid")
        if environment == "production":
            raise ReleaseError("release:production_activation_outside_feature")
        validate_approval(
            owner_approval,
            action=action,
            release_id=candidate["releaseId"],
            environment=environment,
            now=now,
            key=self.approval_key,
        )
        with self.store.locked():
            state = self.store.load()
            if (
                state["candidate"]
                and state["candidate"]["releaseId"] == candidate["releaseId"]
                and action in state["checkpoints"]
            ):
                return self._receipt(state, action, "idempotent")
            if action == "prepare":
                if state["state"] not in {"empty", "promoted", "rolled-back", "halted"}:
                    raise ReleaseError("release:transition_invalid")
                state.update(
                    {
                        "state": "prepared",
                        "environment": environment,
                        "candidate": candidate,
                        "checkpoints": [],
                    }
                )
            else:
                if state["candidate"] != candidate or state["environment"] != environment:
                    raise ReleaseError("release:candidate_mismatch")
                allowed = {
                    "stage": "prepared",
                    "canary": "staged",
                    "promote": "canary",
                    "rollback": "halted",
                }
                if state["state"] != allowed[action]:
                    raise ReleaseError("release:transition_invalid")
                if action in {"stage", "canary", "promote"} and not health(action):
                    state["state"] = "halted"
                    state["checkpoints"].append(f"{action}:failed")
                    state["receipts"].append(self._receipt(state, action, "halted"))
                    self.store.write(state)
                    return state["receipts"][-1]
                if action == "promote":
                    state["previous"], state["current"] = state["current"], candidate
                    state["state"] = "promoted"
                elif action == "rollback":
                    # A halted candidate never received traffic, so selecting the
                    # still-current release is the rollback. Durable data and
                    # migrations are deliberately untouched.
                    if state["current"] is None:
                        raise ReleaseError("release:rollback_unavailable")
                    state["state"] = "rolled-back"
                else:
                    state["state"] = "staged" if action == "stage" else action
            state["checkpoints"].append(action)
            receipt = self._receipt(state, action, state["state"])
            state["receipts"].append(receipt)
            self.store.write(state)
            return receipt

    def status(self) -> dict[str, Any]:
        with self.store.locked():
            state = self.store.load()
            return {
                "state": state["state"],
                "environment": state["environment"],
                "current": state["current"]["releaseId"] if state["current"] else None,
                "candidate": state["candidate"]["releaseId"] if state["candidate"] else None,
                "checkpoints": list(state["checkpoints"]),
            }
