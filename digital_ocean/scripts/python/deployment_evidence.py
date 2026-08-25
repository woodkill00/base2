#!/usr/bin/env python3
"""Atomic, redacted deployment and teardown evidence receipts."""

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
from typing import Any

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{6,126}[A-Za-z0-9]$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CURRENCY = re.compile(r"^[A-Z]{3}$")
STAGE_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
ARTIFACT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SECRET_KEY = re.compile(r"(?:token|password|secret|private.?key|credential|api.?key)", re.I)
FIELDS = {
    "schemaVersion",
    "runId",
    "leaseId",
    "sourceCommit",
    "manifestDigest",
    "action",
    "status",
    "startedAt",
    "finishedAt",
    "stages",
    "cost",
    "artifacts",
    "failure",
}
ACTIONS = {"deploy", "update", "rollback", "teardown", "reconcile", "canary"}
STATUSES = {"running", "passed", "failed", "rolled_back"}
STAGE_STATUSES = {"running", "passed", "failed", "rolled_back", "skipped"}


class EvidenceError(RuntimeError):
    pass


class EvidenceValidationError(EvidenceError):
    pass


class EvidenceIntegrityError(EvidenceError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _timestamp(value: Any, field: str, *, nullable: bool = False) -> datetime | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{field} must be a date-time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceValidationError(f"{field} must be a valid date-time") from exc
    if parsed.tzinfo is None:
        raise EvidenceValidationError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _format(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _reject_secrets(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(str(key)):
                raise EvidenceValidationError("secret-bearing key is forbidden in evidence")
            _reject_secrets(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secrets(child)


def _exact(value: dict, fields: set[str], label: str) -> None:
    unknown = sorted(set(value) - fields)
    missing = sorted(fields - set(value))
    if unknown:
        raise EvidenceValidationError(f"{label} has unknown field {unknown[0]}")
    if missing:
        raise EvidenceValidationError(f"{label} is missing field {missing[0]}")


def validate_evidence(value: Any) -> dict[str, Any]:
    _reject_secrets(value)
    if not isinstance(value, dict):
        raise EvidenceValidationError("evidence must be an object")
    _exact(value, FIELDS, "evidence")
    if value["schemaVersion"] != 1:
        raise EvidenceValidationError("schemaVersion must be 1")
    for field in ("runId", "leaseId"):
        if not isinstance(value[field], str) or not SAFE_ID.fullmatch(value[field]):
            raise EvidenceValidationError(f"{field} is unsafe")
    if not isinstance(value["sourceCommit"], str) or not HEX40.fullmatch(value["sourceCommit"]):
        raise EvidenceValidationError("sourceCommit is invalid")
    if not isinstance(value["manifestDigest"], str) or not HEX64.fullmatch(value["manifestDigest"]):
        raise EvidenceValidationError("manifestDigest is invalid")
    if value["action"] not in ACTIONS or value["status"] not in STATUSES:
        raise EvidenceValidationError("action or status is invalid")
    started = _timestamp(value["startedAt"], "startedAt")
    finished = _timestamp(value["finishedAt"], "finishedAt", nullable=True)
    if value["status"] == "running" and finished is not None:
        raise EvidenceValidationError("running evidence cannot be finished")
    if value["status"] != "running" and finished is None:
        raise EvidenceValidationError("terminal evidence requires finishedAt")
    if finished is not None and finished < started:
        raise EvidenceValidationError("finishedAt precedes startedAt")

    stages = value["stages"]
    if not isinstance(stages, list):
        raise EvidenceValidationError("stages must be an array")
    stage_ids: set[str] = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise EvidenceValidationError("stage must be an object")
        _exact(stage, {"id", "status", "startedAt", "finishedAt", "diagnosticCode"}, "stage")
        if not isinstance(stage["id"], str) or not STAGE_ID.fullmatch(stage["id"]):
            raise EvidenceValidationError("stage id is invalid")
        if stage["id"] in stage_ids:
            raise EvidenceValidationError("stage id is duplicated")
        stage_ids.add(stage["id"])
        if stage["status"] not in STAGE_STATUSES:
            raise EvidenceValidationError("stage status is invalid")
        _timestamp(stage["startedAt"], "stage startedAt")
        stage_finished = _timestamp(stage["finishedAt"], "stage finishedAt", nullable=True)
        if stage["status"] == "running" and stage_finished is not None:
            raise EvidenceValidationError("running stage cannot be finished")
        if stage["status"] != "running" and stage_finished is None:
            raise EvidenceValidationError("terminal stage requires finishedAt")
        if stage["diagnosticCode"] is not None and not isinstance(stage["diagnosticCode"], str):
            raise EvidenceValidationError("diagnosticCode must be text or null")

    cost = value["cost"]
    if not isinstance(cost, dict):
        raise EvidenceValidationError("cost must be an object")
    _exact(
        cost,
        {
            "currency",
            "ceilingMinorUnits",
            "projectedMinorUnits",
            "actualMinorUnits",
            "withinBudget",
        },
        "cost",
    )
    if not isinstance(cost["currency"], str) or not CURRENCY.fullmatch(cost["currency"]):
        raise EvidenceValidationError("cost currency is invalid")
    for field in ("ceilingMinorUnits", "projectedMinorUnits", "actualMinorUnits"):
        if not isinstance(cost[field], int) or isinstance(cost[field], bool) or cost[field] < 0:
            raise EvidenceValidationError(f"cost {field} is invalid")
    expected_budget = (
        max(cost["projectedMinorUnits"], cost["actualMinorUnits"]) <= cost["ceilingMinorUnits"]
    )
    if cost["withinBudget"] is not expected_budget:
        raise EvidenceValidationError("cost withinBudget is inconsistent")

    artifacts = value["artifacts"]
    if not isinstance(artifacts, list):
        raise EvidenceValidationError("artifacts must be an array")
    names: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise EvidenceValidationError("artifact must be an object")
        _exact(artifact, {"name", "sha256", "size"}, "artifact")
        if not isinstance(artifact["name"], str) or not ARTIFACT_NAME.fullmatch(artifact["name"]):
            raise EvidenceValidationError("artifact name is unsafe")
        if artifact["name"] in names:
            raise EvidenceValidationError("artifact name is duplicated")
        names.add(artifact["name"])
        if not isinstance(artifact["sha256"], str) or not HEX64.fullmatch(artifact["sha256"]):
            raise EvidenceValidationError("artifact digest is invalid")
        if not isinstance(artifact["size"], int) or artifact["size"] < 0:
            raise EvidenceValidationError("artifact size is invalid")

    failure = value["failure"]
    if failure is not None:
        if not isinstance(failure, dict):
            raise EvidenceValidationError("failure must be an object or null")
        _exact(failure, {"stage", "code", "retryable"}, "failure")
        if not all(
            isinstance(failure[field], str) and failure[field] for field in ("stage", "code")
        ):
            raise EvidenceValidationError("failure fields are invalid")
        if not isinstance(failure["retryable"], bool):
            raise EvidenceValidationError("failure retryable must be boolean")
    if value["status"] == "failed" and failure is None:
        raise EvidenceValidationError("failed evidence requires failure detail")
    if value["status"] != "failed" and failure is not None:
        raise EvidenceValidationError("non-failed evidence cannot carry failure detail")
    return value


class EvidenceStore:
    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or not self.root.is_dir():
            raise EvidenceIntegrityError("evidence root must be a real directory")
        os.chmod(self.root, 0o700)
        self.lock_path = self.root / ".lock"

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

    def _path(self, run_id: str) -> Path:
        if not isinstance(run_id, str) or not SAFE_ID.fullmatch(run_id):
            raise EvidenceValidationError("runId is unsafe")
        return self.root / f"{run_id}.json"

    def _load(self, run_id: str) -> dict[str, Any]:
        path = self._path(run_id)
        try:
            if path.is_symlink() or not path.is_file():
                raise EvidenceIntegrityError("evidence is unavailable")
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise EvidenceIntegrityError("evidence is not valid JSON") from exc
        if not isinstance(envelope, dict) or set(envelope) != {"evidence", "integrityDigest"}:
            raise EvidenceIntegrityError("evidence envelope is invalid")
        evidence = envelope["evidence"]
        if not isinstance(evidence, dict) or envelope["integrityDigest"] != _digest(evidence):
            raise EvidenceIntegrityError("evidence digest verification failed")
        try:
            return validate_evidence(evidence)
        except EvidenceValidationError as exc:
            raise EvidenceIntegrityError("stored evidence violates its contract") from exc

    def load(self, run_id: str) -> dict[str, Any]:
        with self._lock():
            return self._load(run_id)

    def exists(self, run_id: str) -> bool:
        with self._lock():
            path = self._path(run_id)
            if path.is_symlink():
                raise EvidenceIntegrityError("evidence path must not be a symlink")
            return path.is_file()

    def _write(self, evidence: dict[str, Any]) -> None:
        validate_evidence(evidence)
        target = self._path(evidence["runId"])
        envelope = {"evidence": evidence, "integrityDigest": _digest(evidence)}
        descriptor, name = tempfile.mkstemp(
            prefix=f".{evidence['runId']}.", suffix=".tmp", dir=self.root
        )
        temporary = Path(name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
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

    def create(self, evidence: dict[str, Any]) -> dict[str, Any]:
        validate_evidence(evidence)
        candidate = json.loads(_canonical(evidence))
        with self._lock():
            path = self._path(candidate["runId"])
            if path.exists():
                current = self._load(candidate["runId"])
                if current == candidate:
                    return current
                raise EvidenceIntegrityError("runId already binds different evidence")
            self._write(candidate)
            return candidate

    @staticmethod
    def require_budget(evidence: dict[str, Any]) -> None:
        validate_evidence(evidence)
        if not evidence["cost"]["withinBudget"]:
            raise EvidenceValidationError("projected or actual cost exceeds budget")

    def start_stage(self, run_id: str, stage_id: str, *, now: datetime) -> dict[str, Any]:
        if not STAGE_ID.fullmatch(stage_id):
            raise EvidenceValidationError("stage id is invalid")
        with self._lock():
            evidence = self._load(run_id)
            if evidence["status"] != "running":
                raise EvidenceValidationError("terminal evidence cannot start a stage")
            if any(item["id"] == stage_id for item in evidence["stages"]):
                raise EvidenceValidationError("stage id is duplicated")
            updated = json.loads(_canonical(evidence))
            updated["stages"].append(
                {
                    "id": stage_id,
                    "status": "running",
                    "startedAt": _format(now),
                    "finishedAt": None,
                    "diagnosticCode": None,
                }
            )
            self._write(updated)
            return updated

    def finish_stage(
        self,
        run_id: str,
        stage_id: str,
        status: str,
        *,
        now: datetime,
        diagnostic_code: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"passed", "failed", "rolled_back", "skipped"}:
            raise EvidenceValidationError("terminal stage status is invalid")
        with self._lock():
            evidence = self._load(run_id)
            updated = json.loads(_canonical(evidence))
            matches = [item for item in updated["stages"] if item["id"] == stage_id]
            if len(matches) != 1 or matches[0]["status"] != "running":
                raise EvidenceValidationError("stage is not running")
            matches[0].update(
                status=status, finishedAt=_format(now), diagnosticCode=diagnostic_code
            )
            self._write(updated)
            return updated

    def finish_failure(
        self, run_id: str, *, stage: str, code: str, retryable: bool, now: datetime
    ) -> dict[str, Any]:
        self.finish_stage(run_id, stage, "failed", now=now, diagnostic_code=code)
        with self._lock():
            evidence = self._load(run_id)
            updated = {
                **evidence,
                "status": "failed",
                "finishedAt": _format(now),
                "failure": {"stage": stage, "code": code, "retryable": retryable},
            }
            self._write(updated)
            return updated

    def finish_success(
        self, run_id: str, *, actual_minor_units: int, now: datetime
    ) -> dict[str, Any]:
        with self._lock():
            evidence = self._load(run_id)
            if any(item["status"] == "running" for item in evidence["stages"]):
                raise EvidenceValidationError("running stage prevents successful completion")
            updated = json.loads(_canonical(evidence))
            updated["cost"]["actualMinorUnits"] = actual_minor_units
            updated["cost"]["withinBudget"] = (
                max(updated["cost"]["projectedMinorUnits"], actual_minor_units)
                <= updated["cost"]["ceilingMinorUnits"]
            )
            self.require_budget(updated)
            updated.update(status="passed", finishedAt=_format(now), failure=None)
            self._write(updated)
            return updated


class EvidenceRun:
    """Small orchestration adapter that makes every invoked stage terminal."""

    def __init__(
        self,
        store: EvidenceStore,
        evidence: dict[str, Any],
        *,
        clock=lambda: datetime.now(UTC),
    ) -> None:
        self.store = store
        self.evidence = store.create(evidence)
        self.store.require_budget(self.evidence)
        self.clock = clock

    def execute(
        self,
        stage_id: str,
        operation,
        *,
        failure_code: str,
        retryable: bool = False,
    ) -> Any:
        self.store.start_stage(self.evidence["runId"], stage_id, now=self.clock())
        try:
            result = operation()
        except Exception:
            self.store.finish_failure(
                self.evidence["runId"],
                stage=stage_id,
                code=failure_code,
                retryable=retryable,
                now=self.clock(),
            )
            raise
        self.store.finish_stage(self.evidence["runId"], stage_id, "passed", now=self.clock())
        return result

    def complete(self, *, actual_minor_units: int) -> dict[str, Any]:
        return self.store.finish_success(
            self.evidence["runId"],
            actual_minor_units=actual_minor_units,
            now=self.clock(),
        )
