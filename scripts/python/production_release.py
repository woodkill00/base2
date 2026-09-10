#!/usr/bin/env python3
"""Provider-neutral, fail-closed immutable release lifecycle."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import re
import stat
import subprocess
import uuid
from collections.abc import Callable
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RELEASE_ID = re.compile(r"^release-[A-Za-z0-9._-]{4,120}$")
IMAGE = re.compile(r"^[a-z0-9][a-z0-9./_-]{2,190}@sha256:[0-9a-f]{64}$")
ENVIRONMENTS = {"development", "test", "preview", "staging", "production"}
ACTIONS = {"prepare", "preview", "stage", "canary", "promote", "rollback"}
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
    "sourceCommit",
    "artifactDigest",
    "expiresAt",
    "digest",
}
OPERATION_FIELDS = {
    "schemaVersion",
    "operationId",
    "action",
    "releaseId",
    "environment",
    "sourceCommit",
    "artifactDigest",
    "status",
    "observedAt",
    "expiresAt",
    "digest",
}
HEALTH_FIELDS = {
    "schemaVersion",
    "operationId",
    "action",
    "releaseId",
    "environment",
    "sourceCommit",
    "artifactDigest",
    "healthy",
    "observedAt",
    "expiresAt",
    "digest",
}


class ReleaseError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _tree_digest(root: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        if path.is_symlink() or not path.is_file():
            raise ReleaseError("release:source_file_unsafe")
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def build_release_manifest(
    *,
    root: Path,
    release_id: str,
    images: dict[str, str],
    sbom_path: Path,
    provenance_path: Path,
    now: datetime,
    key: bytes,
) -> dict[str, Any]:
    """Build one manifest from an exact clean checkout and immutable inputs."""
    if now.tzinfo is None:
        raise ReleaseError("release:time_invalid")
    repository = root.resolve()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            text=True,
            capture_output=True,
            timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            check=True,
            text=True,
            capture_output=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReleaseError("release:source_unavailable") from exc
    if status:
        raise ReleaseError("release:source_dirty")
    migration_paths = list((repository / "django").glob("*/migrations/*.py"))
    configuration_paths = [
        *list((repository / "shared/config").glob("*.json")),
        *list((repository / "shared/schemas").glob("*.json")),
        *list(repository.glob("*.docker.yml")),
    ]
    if not migration_paths or not configuration_paths:
        raise ReleaseError("release:source_inventory_incomplete")
    for external in (sbom_path, provenance_path):
        resolved = external.resolve()
        if external.is_symlink() or not resolved.is_file() or repository not in resolved.parents:
            raise ReleaseError("release:source_file_unsafe")
    readiness = json.loads(
        (repository / "shared/config/production-readiness-v1.json").read_text(encoding="utf-8")
    )
    candidate = {
        "schemaVersion": 2,
        "releaseId": release_id,
        "sourceCommit": commit,
        "sourceClean": True,
        "images": images,
        "migrationsDigest": _tree_digest(repository, migration_paths),
        "configurationSchemaVersion": int(readiness["schemaVersion"]),
        "configurationDigest": _tree_digest(repository, configuration_paths),
        "sbomDigest": hashlib.sha256(sbom_path.read_bytes()).hexdigest(),
        "provenanceDigest": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
        "createdAt": now.astimezone(UTC).isoformat(),
    }
    return sign_release(candidate, key=key)


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
    source_commit: str,
    artifact_digest: str,
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
        "sourceCommit": source_commit,
        "artifactDigest": artifact_digest,
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
    source_commit: str,
    artifact_digest: str,
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
        or value["sourceCommit"] != source_commit
        or value["artifactDigest"] != artifact_digest
    ):
        raise ReleaseError("approval:scope_mismatch")
    expiry = _time(value["expiresAt"])
    if (
        now.tzinfo is None
        or now.astimezone(UTC) >= expiry
        or expiry - now.astimezone(UTC) > timedelta(minutes=15)
    ):
        raise ReleaseError("approval:expired")


def operation_receipt(
    *,
    operation_id: str,
    action: str,
    release_id: str,
    environment: str,
    source_commit: str,
    artifact_digest: str,
    status: str,
    observed_at: datetime,
    expires_at: datetime,
    key: bytes,
) -> dict[str, Any]:
    if (
        len(key) < 32
        or not re.fullmatch(r"operation-[A-Za-z0-9._-]{4,120}", operation_id or "")
        or action not in ACTIONS - {"prepare", "preview"}
        or not RELEASE_ID.fullmatch(release_id or "")
        or environment not in ENVIRONMENTS - {"production"}
        or status not in {"succeeded", "failed"}
        or observed_at.tzinfo is None
        or expires_at.tzinfo is None
        or not HEX40.fullmatch(source_commit or "")
        or not HEX64.fullmatch(artifact_digest or "")
        or not observed_at < expires_at
        or expires_at - observed_at > timedelta(minutes=15)
    ):
        raise ReleaseError("release:operation_receipt_invalid")
    value = {
        "schemaVersion": 1,
        "operationId": operation_id,
        "action": action,
        "releaseId": release_id,
        "environment": environment,
        "sourceCommit": source_commit,
        "artifactDigest": artifact_digest,
        "status": status,
        "observedAt": observed_at.astimezone(UTC).isoformat(),
        "expiresAt": expires_at.astimezone(UTC).isoformat(),
    }
    value["digest"] = hmac.new(key, _canonical(value), hashlib.sha256).hexdigest()
    return value


def validate_operation_receipt(
    value: Any,
    *,
    action: str,
    release_id: str,
    environment: str,
    source_commit: str,
    artifact_digest: str,
    operation_id: str,
    now: datetime,
    key: bytes,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != OPERATION_FIELDS:
        raise ReleaseError("release:operation_receipt_invalid")
    rebuilt = operation_receipt(
        operation_id=value["operationId"],
        action=value["action"],
        release_id=value["releaseId"],
        environment=value["environment"],
        source_commit=value["sourceCommit"],
        artifact_digest=value["artifactDigest"],
        status=value["status"],
        observed_at=_time(value["observedAt"]),
        expires_at=_time(value["expiresAt"]),
        key=key,
    )
    if rebuilt != value:
        raise ReleaseError("release:operation_receipt_integrity")
    if (
        value["action"] != action
        or value["operationId"] != operation_id
        or value["releaseId"] != release_id
        or value["environment"] != environment
        or value["sourceCommit"] != source_commit
        or value["artifactDigest"] != artifact_digest
    ):
        raise ReleaseError("release:operation_receipt_scope_mismatch")
    if now.tzinfo is None or not _time(value["observedAt"]) <= now.astimezone(UTC) < _time(
        value["expiresAt"]
    ):
        raise ReleaseError("release:operation_receipt_expired")
    return json.loads(json.dumps(value))


def health_receipt(
    *,
    operation_id: str,
    action: str,
    release_id: str,
    environment: str,
    source_commit: str,
    artifact_digest: str,
    healthy: bool,
    observed_at: datetime,
    expires_at: datetime,
    key: bytes,
) -> dict[str, Any]:
    if (
        len(key) < 32
        or not re.fullmatch(r"operation-[A-Za-z0-9._-]{4,120}", operation_id or "")
        or action not in {"stage", "canary", "promote"}
        or not RELEASE_ID.fullmatch(release_id or "")
        or environment not in ENVIRONMENTS - {"production"}
        or type(healthy) is not bool
        or observed_at.tzinfo is None
        or expires_at.tzinfo is None
        or not HEX40.fullmatch(source_commit or "")
        or not HEX64.fullmatch(artifact_digest or "")
        or not observed_at < expires_at
        or expires_at - observed_at > timedelta(minutes=5)
    ):
        raise ReleaseError("release:health_receipt_invalid")
    value = {
        "schemaVersion": 1,
        "operationId": operation_id,
        "action": action,
        "releaseId": release_id,
        "environment": environment,
        "sourceCommit": source_commit,
        "artifactDigest": artifact_digest,
        "healthy": healthy,
        "observedAt": observed_at.astimezone(UTC).isoformat(),
        "expiresAt": expires_at.astimezone(UTC).isoformat(),
    }
    value["digest"] = hmac.new(key, _canonical(value), hashlib.sha256).hexdigest()
    return value


def validate_health_receipt(
    value: Any,
    *,
    action: str,
    release_id: str,
    environment: str,
    source_commit: str,
    artifact_digest: str,
    operation_id: str,
    operation_observed_at: datetime,
    now: datetime,
    key: bytes,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != HEALTH_FIELDS:
        raise ReleaseError("release:health_receipt_invalid")
    rebuilt = health_receipt(
        operation_id=value["operationId"],
        action=value["action"],
        release_id=value["releaseId"],
        environment=value["environment"],
        source_commit=value["sourceCommit"],
        artifact_digest=value["artifactDigest"],
        healthy=value["healthy"],
        observed_at=_time(value["observedAt"]),
        expires_at=_time(value["expiresAt"]),
        key=key,
    )
    if rebuilt != value:
        raise ReleaseError("release:health_receipt_integrity")
    if (
        value["action"] != action
        or value["operationId"] != operation_id
        or value["releaseId"] != release_id
        or value["environment"] != environment
        or value["sourceCommit"] != source_commit
        or value["artifactDigest"] != artifact_digest
    ):
        raise ReleaseError("release:health_receipt_scope_mismatch")
    if operation_observed_at.tzinfo is None or _time(value["observedAt"]) <= operation_observed_at.astimezone(UTC):
        raise ReleaseError("release:health_receipt_precedes_operation")
    if now.tzinfo is None or not _time(value["observedAt"]) <= now.astimezone(UTC) < _time(
        value["expiresAt"]
    ):
        raise ReleaseError("release:health_receipt_expired")
    return json.loads(json.dumps(value))


class ReleaseJournal:
    def __init__(self, path: Path, *, key: bytes):
        self.path = path
        self.key = key
        self.lock = path.with_suffix(path.suffix + ".lock")
        self._directory_fd: int | None = None

    def _open_parent(self) -> tuple[int, str]:
        candidate = Path(os.path.abspath(self.path))
        if candidate.name in {"", ".", ".."} or "/" in candidate.name:
            raise ReleaseError("release:journal_path_invalid")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        descriptor = os.open("/", flags)
        try:
            for part in candidate.parent.parts[1:]:
                child = os.open(part, flags, dir_fd=descriptor)
                try:
                    details = os.fstat(child)
                    unsafe_writable = details.st_mode & 0o022 and not details.st_mode & stat.S_ISVTX
                    if not stat.S_ISDIR(details.st_mode) or unsafe_writable:
                        raise ReleaseError("release:journal_parent_unsafe")
                except Exception:
                    os.close(child)
                    raise
                os.close(descriptor)
                descriptor = child
            details = os.fstat(descriptor)
            if details.st_uid != os.geteuid() or stat.S_IMODE(details.st_mode) != 0o700:
                raise ReleaseError("release:journal_parent_not_private")
            return descriptor, candidate.name
        except Exception:
            os.close(descriptor)
            raise

    @staticmethod
    def _require_private_member(descriptor: int, diagnostic: str) -> None:
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or details.st_uid != os.geteuid()
            or details.st_nlink != 1
            or stat.S_IMODE(details.st_mode) != 0o600
        ):
            raise ReleaseError(diagnostic)

    @contextmanager
    def locked(self):
        try:
            directory_fd, name = self._open_parent()
        except OSError as exc:
            raise ReleaseError("release:journal_parent_unsafe") from exc
        lock_name = f"{name}.lock"
        flags = os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW
        descriptor = None
        try:
            try:
                descriptor = os.open(lock_name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory_fd)
            except FileExistsError:
                descriptor = os.open(lock_name, flags, dir_fd=directory_fd)
            self._require_private_member(descriptor, "release:journal_lock_unsafe")
        except OSError as exc:
            if descriptor is not None:
                os.close(descriptor)
            os.close(directory_fd)
            raise ReleaseError("release:journal_lock_unsafe") from exc
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            os.close(directory_fd)
            raise
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(descriptor)
            os.close(directory_fd)
            raise ReleaseError("release:concurrent_runner") from exc
        except Exception:
            os.close(descriptor)
            os.close(directory_fd)
            raise
        self._directory_fd = directory_fd
        try:
            yield
        finally:
            self._directory_fd = None
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
                os.close(directory_fd)

    def load(self) -> dict[str, Any]:
        if self._directory_fd is None:
            raise ReleaseError("release:journal_lock_required")
        try:
            descriptor = os.open(
                self.path.name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=self._directory_fd,
            )
        except FileNotFoundError:
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
        except OSError as exc:
            raise ReleaseError("release:journal_unsafe") from exc
        try:
            self._require_private_member(descriptor, "release:journal_unsafe")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ReleaseError("release:journal_invalid")
            envelope = json.loads(raw.decode("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            raise ReleaseError("release:journal_invalid") from exc
        finally:
            os.close(descriptor)
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
        if self._directory_fd is None:
            raise ReleaseError("release:journal_lock_required")
        envelope = {
            "journal": state,
            "integrity": hmac.new(self.key, _canonical(state), hashlib.sha256).hexdigest(),
        }
        temporary = f".release-{uuid.uuid4().hex}.tmp"
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=self._directory_fd,
        )
        try:
            self._require_private_member(descriptor, "release:journal_temporary_unsafe")
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(_canonical(envelope) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            try:
                existing = os.open(
                    self.path.name,
                    os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                    dir_fd=self._directory_fd,
                )
            except FileNotFoundError:
                existing = None
            except OSError as exc:
                raise ReleaseError("release:journal_unsafe") from exc
            if existing is not None:
                try:
                    self._require_private_member(existing, "release:journal_unsafe")
                finally:
                    os.close(existing)
            os.replace(
                temporary,
                self.path.name,
                src_dir_fd=self._directory_fd,
                dst_dir_fd=self._directory_fd,
            )
            os.fsync(self._directory_fd)
        finally:
            os.close(descriptor)
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=self._directory_fd)


class ProductionReleaseController:
    def __init__(self, path: Path, *, release_key: bytes, approval_key: bytes):
        if len(release_key) < 32 or len(approval_key) < 32 or release_key == approval_key:
            raise ReleaseError("release:key_invalid")
        self.store = ReleaseJournal(path, key=release_key)
        self.release_key = release_key
        self.approval_key = approval_key

    def _receipt(
        self, state: dict[str, Any], action: str, status: str, now: datetime
    ) -> dict[str, Any]:
        candidate = state["candidate"]
        value = {
            "schemaVersion": 1,
            "action": action,
            "status": status,
            "environment": state["environment"],
            "releaseId": candidate["releaseId"] if candidate else None,
            "sourceCommit": candidate["sourceCommit"] if candidate else None,
            "artifactDigest": candidate["artifactDigest"] if candidate else None,
            "checkpointCount": len(state["checkpoints"]),
            "checkpointDigest": _digest(state["checkpoints"]),
            "observedAt": now.astimezone(UTC).isoformat(),
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
        health: Callable[[str], bool] | None = None,
        execute: Callable[[str, dict[str, Any], str, str, bool], dict[str, Any]] | None = None,
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
            source_commit=candidate["sourceCommit"],
            artifact_digest=candidate["artifactDigest"],
            now=now,
            key=self.approval_key,
        )
        with self.store.locked():
            state = self.store.load()
            if (
                state["candidate"]
                and state["candidate"] == candidate
                and state["environment"] == environment
                and action in state["checkpoints"]
            ):
                return self._receipt(state, action, "idempotent", now)
            if action in {"prepare", "preview"}:
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
                if action in {"stage", "canary", "promote"} and health is None:
                    raise ReleaseError("release:health_adapter_required")
                if execute is None:
                    raise ReleaseError("release:execution_adapter_required")
                started = f"{action}:started"
                reconcile_only = started in state["checkpoints"]
                operation_id = (
                    "operation-"
                    + _digest(
                        {
                            "action": action,
                            "releaseId": candidate["releaseId"],
                            "environment": environment,
                            "sourceCommit": candidate["sourceCommit"],
                            "artifactDigest": candidate["artifactDigest"],
                        }
                    )[:24]
                )
                if not reconcile_only:
                    state["checkpoints"].append(started)
                    state["receipts"].append(self._receipt(state, action, "started", now))
                    self.store.write(state)
                try:
                    operation = execute(
                        action, candidate, environment, operation_id, reconcile_only
                    )
                except Exception:
                    interrupted = f"{action}:interrupted"
                    if interrupted not in state["checkpoints"]:
                        state["checkpoints"].append(interrupted)
                    state["receipts"].append(self._receipt(state, action, "pending", now))
                    self.store.write(state)
                    return state["receipts"][-1]
                if (
                    not isinstance(operation, dict)
                    or operation.get("status") != "succeeded"
                    or operation.get("action") != action
                    or operation.get("releaseId") != candidate["releaseId"]
                    or operation.get("environment") != environment
                    or operation.get("operationId") != operation_id
                    or operation.get("sourceCommit") != candidate["sourceCommit"]
                    or operation.get("artifactDigest") != candidate["artifactDigest"]
                ):
                    state["state"] = "halted"
                    state["checkpoints"].append(f"{action}:execution-failed")
                    state["receipts"].append(self._receipt(state, action, "halted", now))
                    self.store.write(state)
                    return state["receipts"][-1]
                if action in {"stage", "canary", "promote"} and not health(action):
                    state["state"] = "halted"
                    state["checkpoints"].append(f"{action}:failed")
                    state["receipts"].append(self._receipt(state, action, "halted", now))
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
            receipt = self._receipt(state, action, state["state"], now)
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
