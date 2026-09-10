#!/usr/bin/env python3
"""Run the fixed Base2 complete gate and emit integrity-bound evidence."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import uuid
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path

SECRET_KEY = re.compile(r"(?:TOKEN|PASSWORD|SECRET|PRIVATE|CREDENTIAL|API_KEY)", re.I)
INLINE_SECRET = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
TERMINAL_TEST_SUMMARY = re.compile(
    r"(?im)^(?:\s*(?:Test Files|Tests)\s+|\s*Ran \d+ tests?\b|"
    r"\s*\d+\s+(?:passed|failed|errors?)\b|\s*=+.*\b(?:passed|failed|errors?)\b.*=+\s*$)"
)
INFRASTRUCTURE_CRASH = re.compile(
    r"(?i)\b(?:SIGSEGV|segmentation fault|Worker exited unexpectedly|"
    r"Worker forks emitted error)\b"
)
TOOL_TOKENS = {
    "{python-api}": (".venv-api/bin/python", ".venv-api/Scripts/python.exe"),
    "{python-django}": (".venv-django/bin/python", ".venv-django/Scripts/python.exe"),
    "{python-orchestrator}": (".venv/bin/python", ".venv/Scripts/python.exe"),
}
GATE_BUSY_EXIT = 3


class CompleteGateBusy(RuntimeError):
    """Another process owns the repository-wide complete-gate lease."""


def _contained_parts(path: Path, trusted_root: Path) -> tuple[str, ...]:
    root = Path(os.path.abspath(trusted_root))
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("private_path_outside_trusted_root") from exc
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("invalid_private_path")
    return relative.parts


def open_private_directory(path: Path, trusted_root: Path, *, create: bool = True) -> int:
    """Open a contained private directory chain without following links."""
    parts = _contained_parts(path, trusted_root)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(Path(os.path.abspath(trusted_root)), flags)
    try:
        for part in parts:
            if create:
                with suppress(FileExistsError):
                    os.mkdir(part, 0o700, dir_fd=descriptor)
            child = os.open(part, flags, dir_fd=descriptor)
            try:
                details = os.fstat(child)
                if (
                    not stat.S_ISDIR(details.st_mode)
                    or details.st_uid != os.geteuid()
                    or (not create and stat.S_IMODE(details.st_mode) != 0o700)
                ):
                    raise ValueError("unsafe_private_directory")
                if create:
                    os.fchmod(child, 0o700)
            except Exception:
                os.close(child)
                raise
            os.close(descriptor)
            descriptor = child
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def open_private_file(directory_fd: int, name: str, *, truncate: bool = True) -> int:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise ValueError("invalid_private_member_name")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    if truncate:
        flags |= os.O_TRUNC
    descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
    try:
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or details.st_uid != os.geteuid()
            or details.st_nlink != 1
        ):
            raise ValueError("unsafe_private_member")
        os.fchmod(descriptor, 0o600)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def private_write(directory_fd: int, name: str, data: bytes) -> tuple[str, int]:
    descriptor = open_private_file(directory_fd, name)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    return hashlib.sha256(data).hexdigest(), len(data)


def private_atomic_json(directory_fd: int, name: str, payload: dict) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    temporary = f".{name}.{uuid.uuid4().hex}.tmp"
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory_fd,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            existing = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and (
            not stat.S_ISREG(existing.st_mode) or existing.st_uid != os.geteuid()
        ):
            raise ValueError("unsafe_private_result_member")
        os.replace(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        os.close(descriptor)
        with suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=directory_fd)


@contextmanager
def complete_gate_lock(repo_root: Path):
    artifacts_fd = open_private_directory(repo_root / ".artifacts", repo_root)
    lock_path = repo_root / ".artifacts" / "complete-gate.lock"
    descriptor = None
    try:
        descriptor = os.open(
            "complete-gate.lock",
            os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=artifacts_fd,
        )
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or details.st_uid != os.geteuid()
            or details.st_nlink != 1
        ):
            raise ValueError("unsafe_complete_gate_lock")
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, "r+")
        descriptor = None
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        os.close(artifacts_fd)
        raise
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CompleteGateBusy("complete_gate_already_running") from exc
        yield lock_path
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            os.close(artifacts_fd)


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def validate_runtime_capacity() -> None:
    """Fail early on a WSL allocation known to destabilize browser/V8 gates."""
    if "microsoft" in platform.release().lower() and (os.cpu_count() or 1) < 2:
        raise RuntimeError(
            "complete gate requires at least 2 WSL processors; set processors=2 or higher "
            "under [wsl2] in the Windows user .wslconfig, then run wsl --shutdown"
        )


def retryable_interpreter_corruption(output: str) -> bool:
    """Recognize the observed impossible JSON encoder state without masking app failures."""
    json_encoder_corruption = (
        "/json/encoder.py" in output
        and "yield '\\n' + _indent * _current_indent_level" in output
        and "TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'" in output
    )
    django_field_counter_corruption = (
        "/django/db/models/fields/__init__.py" in output
        and "Field.creation_counter += 1" in output
        and "TypeError: unsupported operand type(s) for +=: 'type' and 'int'" in output
    )
    return json_encoder_corruption or django_field_counter_corruption


def validate_manifest(manifest: dict) -> None:
    if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("checks"), list):
        raise ValueError("unsupported complete-gate manifest")
    checks = manifest["checks"]
    ids = [item.get("id") for item in checks]
    if any(not isinstance(item, str) or not re.fullmatch(r"[a-z][a-z0-9-]+", item) for item in ids):
        raise ValueError("invalid check ID")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate check ID")
    known = set(ids)
    graph = {}
    for item in checks:
        allowed = {
            "id",
            "command",
            "required",
            "timeoutSeconds",
            "dependsOn",
            "requiredTools",
            "maxAttempts",
            "retryOn",
        }
        required_fields = {
            "id",
            "command",
            "required",
            "timeoutSeconds",
            "dependsOn",
            "requiredTools",
        }
        if not required_fields <= set(item) or not set(item) <= allowed:
            raise ValueError(f"invalid fields for {item.get('id')}")
        if (
            not isinstance(item["command"], list)
            or not item["command"]
            or not all(isinstance(value, str) and value for value in item["command"])
        ):
            raise ValueError(f"invalid command for {item['id']}")
        for dependency in item["dependsOn"]:
            if dependency not in known:
                raise ValueError(f"unknown dependency {dependency}")
        graph[item["id"]] = item["dependsOn"]
        max_attempts = item.get("maxAttempts", 2)
        retry_on = item.get("retryOn", [])
        if max_attempts not in (1, 2):
            raise ValueError(f"invalid maxAttempts for {item['id']}")
        if not isinstance(retry_on, list) or any(
            value not in {"timeout", "incomplete-test-output"} for value in retry_on
        ):
            raise ValueError(f"invalid retryOn for {item['id']}")

    visiting = set()
    visited = set()

    def visit(check_id: str) -> None:
        if check_id in visited:
            return
        if check_id in visiting:
            raise ValueError("dependency cycle")
        visiting.add(check_id)
        for dependency in graph[check_id]:
            visit(dependency)
        visiting.remove(check_id)
        visited.add(check_id)

    for check_id in ids:
        visit(check_id)


def dependency_ordered_checks(manifest: dict) -> list[dict]:
    """Return a stable topological order independent of declaration order."""
    pending = list(manifest["checks"])
    ordered = []
    emitted = set()
    while pending:
        ready = [item for item in pending if set(item["dependsOn"]) <= emitted]
        if not ready:
            raise ValueError("dependency cycle")
        for item in ready:
            ordered.append(item)
            emitted.add(item["id"])
            pending.remove(item)
    return ordered


def resolve_tool(tool: str, repo_root: Path) -> str:
    if tool in TOOL_TOKENS:
        candidates = TOOL_TOKENS[tool]
        selected = candidates[1] if os.name == "nt" else candidates[0]
        return str(repo_root / selected)
    return tool


def tool_available(tool: str, repo_root: Path) -> bool:
    tool = resolve_tool(tool, repo_root)
    if "/" in tool or "\\" in tool:
        candidate = Path(tool)
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        return candidate.is_file() and os.access(candidate, os.X_OK)
    return shutil.which(tool) is not None


def redact(text: str, environment: dict[str, str]) -> str:
    output = INLINE_SECRET.sub(r"\1[REDACTED]", text)
    values = {
        str(value)
        for key, value in environment.items()
        if SECRET_KEY.search(key) and value is not None and len(str(value)) >= 4
    }
    for value in sorted(values, key=len, reverse=True):
        output = output.replace(value, "[REDACTED]")
    return output


def run_gate(
    manifest: dict,
    repo_root: Path,
    evidence_dir: Path,
    *,
    source_commit: str,
    environment: dict[str, str] | None = None,
) -> dict:
    validate_manifest(manifest)
    repo_root = repo_root.resolve()
    evidence_fd = open_private_directory(evidence_dir, repo_root)
    try:
        return _run_gate(
            manifest,
            repo_root,
            evidence_dir,
            evidence_fd,
            source_commit=source_commit,
            environment=environment,
        )
    finally:
        os.close(evidence_fd)


def _run_gate(
    manifest: dict,
    repo_root: Path,
    evidence_dir: Path,
    evidence_fd: int,
    *,
    source_commit: str,
    environment: dict[str, str] | None = None,
) -> dict:
    environment = dict(environment or os.environ)
    environment["PYTHONHASHSEED"] = "0"
    environment["PYTHONMALLOC"] = "malloc"
    started = now()
    results = []
    states = {}

    for item in dependency_ordered_checks(manifest):
        check_id = item["id"]
        base = {
            "id": check_id,
            "required": item["required"],
            "exitCode": None,
            "artifact": None,
            "diagnostic": None,
            "attempts": 0,
        }
        blocked = [
            dependency for dependency in item["dependsOn"] if states.get(dependency) != "passed"
        ]
        if blocked:
            result = {
                **base,
                "status": "not_run",
                "diagnostic": "blocked by: " + ", ".join(blocked),
            }
        else:
            missing = [
                tool for tool in item["requiredTools"] if not tool_available(tool, repo_root)
            ]
            if missing:
                result = {
                    **base,
                    "status": "unavailable",
                    "diagnostic": "missing tools: " + ", ".join(missing),
                }
            else:
                artifact = evidence_dir / f"{check_id}.log"
                try:
                    command = [resolve_tool(value, repo_root) for value in item["command"]]
                    outputs = []
                    attempts = 0
                    timed_out = False
                    retry_on = set(item.get("retryOn", []))
                    max_attempts = item.get("maxAttempts", 2)
                    while attempts < max_attempts:
                        attempts += 1
                        try:
                            completed = subprocess.run(
                                command,
                                cwd=repo_root,
                                env=environment,
                                text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                timeout=item["timeoutSeconds"],
                                check=False,
                            )
                        except subprocess.TimeoutExpired as exc:
                            timed_out = True
                            captured = exc.stdout or ""
                            if isinstance(captured, bytes):
                                captured = captured.decode(errors="replace")
                            outputs.append(
                                f"=== attempt {attempts} timeout after {item['timeoutSeconds']} seconds ===\n{captured}"
                            )
                            if "timeout" in retry_on and attempts < max_attempts:
                                continue
                            break
                        timed_out = False
                        outputs.append(
                            f"=== attempt {attempts} exit {completed.returncode} ===\n{completed.stdout or ''}"
                        )
                        captured_output = completed.stdout or ""
                        incomplete = (
                            completed.returncode != 0
                            and "incomplete-test-output" in retry_on
                            and not TERMINAL_TEST_SUMMARY.search(captured_output)
                        )
                        # Direct processes report SIGSEGV as -11 while shell/npm
                        # wrappers conventionally translate the same signal to
                        # 128 + 11. Treat both as the existing bounded
                        # infrastructure retry, never as an application pass.
                        infrastructure_crash = (
                            completed.returncode in {-11, 139}
                            or INFRASTRUCTURE_CRASH.search(captured_output) is not None
                            or retryable_interpreter_corruption(captured_output)
                        )
                        if not infrastructure_crash and not incomplete:
                            break
                    artifact_bytes = redact("\n".join(outputs), environment).encode()
                    artifact_sha256, artifact_size = private_write(
                        evidence_fd, artifact.name, artifact_bytes
                    )
                    exit_code = None if timed_out else completed.returncode
                    status = "passed" if not timed_out and exit_code == 0 else "failed"
                    result = {
                        **base,
                        "status": status,
                        "exitCode": exit_code,
                        "artifact": artifact.name,
                        "artifactSha256": artifact_sha256,
                        "artifactSize": artifact_size,
                        "attempts": attempts,
                    }
                    if status == "passed" and attempts > 1:
                        result["diagnostic"] = "recovered after one bounded infrastructure retry"
                    if status == "failed":
                        if timed_out:
                            result["diagnostic"] = (
                                f"timed out after {item['timeoutSeconds']} seconds"
                                + (" after one bounded retry" if attempts > 1 else "")
                            )
                        else:
                            suffix = " after one bounded retry" if attempts > 1 else ""
                            result["diagnostic"] = f"command exited {exit_code}{suffix}"
                except Exception:
                    raise
        states[check_id] = result["status"]
        results.append(result)

    required_states = [item["status"] for item in results if item["required"]]
    if "failed" in required_states:
        overall = "failed"
    elif any(status != "passed" for status in required_states):
        overall = "incomplete"
    else:
        overall = "passed"

    payload = {
        "schemaVersion": 1,
        "runId": f"complete-gate-{uuid.uuid4().hex}",
        "sourceCommit": source_commit,
        "startedAt": started,
        "finishedAt": now(),
        "overallStatus": overall,
        "checks": results,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidenceDigest"] = hashlib.sha256(canonical).hexdigest()
    private_atomic_json(evidence_fd, "result.json", payload)
    validate_gate_evidence(evidence_dir / "result.json", repo_root)
    return payload


def validate_gate_evidence(result_path: Path, repo_root: Path) -> dict:
    evidence_fd = open_private_directory(result_path.parent, repo_root, create=False)
    try:
        descriptor = os.open(
            result_path.name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=evidence_fd
        )
        try:
            handle = os.fdopen(descriptor, "rb")
        except Exception:
            os.close(descriptor)
            raise
        with handle:
            details = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(details.st_mode)
                or details.st_uid != os.geteuid()
                or details.st_nlink != 1
                or stat.S_IMODE(details.st_mode) != 0o600
            ):
                raise ValueError("complete_gate_result_unsafe")
            payload = json.loads(handle.read())
        expected_digest = payload.pop("evidenceDigest", None)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        if expected_digest != hashlib.sha256(canonical).hexdigest():
            raise ValueError("complete_gate_result_digest_invalid")
        seen = set()
        for item in payload.get("checks", []):
            artifact = item.get("artifact")
            if artifact is None:
                continue
            if artifact in seen or not re.fullmatch(r"[a-z][a-z0-9-]+\.log", artifact):
                raise ValueError("complete_gate_artifact_name_invalid")
            seen.add(artifact)
            member = os.open(
                artifact, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=evidence_fd
            )
            try:
                details = os.fstat(member)
                if (
                    not stat.S_ISREG(details.st_mode)
                    or details.st_uid != os.geteuid()
                    or details.st_nlink != 1
                    or stat.S_IMODE(details.st_mode) != 0o600
                ):
                    raise ValueError("complete_gate_artifact_unsafe")
                artifact_digest = hashlib.sha256()
                artifact_size = 0
                while True:
                    block = os.read(member, 1024 * 1024)
                    if not block:
                        break
                    artifact_digest.update(block)
                    artifact_size += len(block)
            finally:
                os.close(member)
            if (
                item.get("artifactSize") != artifact_size
                or item.get("artifactSha256") != artifact_digest.hexdigest()
            ):
                raise ValueError("complete_gate_artifact_integrity_invalid")
        return {**payload, "evidenceDigest": expected_digest}
    finally:
        os.close(evidence_fd)


def git_commit(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, capture_output=True, check=True
    )
    return completed.stdout.strip()


def write_busy_receipt(repo_root: Path) -> Path:
    started = now()
    run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"
    path = repo_root / ".artifacts" / "complete-gate-busy" / run_id / "result.json"
    payload = {
        "schemaVersion": 1,
        "runId": f"complete-gate-busy-{uuid.uuid4().hex}",
        "sourceCommit": None,
        "startedAt": started,
        "finishedAt": now(),
        "overallStatus": "busy",
        "diagnostic": "complete_gate_already_running",
        "checks": [],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidenceDigest"] = hashlib.sha256(canonical).hexdigest()
    directory_fd = open_private_directory(path.parent, repo_root)
    try:
        private_atomic_json(directory_fd, path.name, payload)
    finally:
        os.close(directory_fd)
    return path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        with complete_gate_lock(repo_root):
            validate_runtime_capacity()
            manifest_path = repo_root / "scripts" / "config" / "complete-gate-v1.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"
            evidence_dir = repo_root / ".artifacts" / "complete-gate" / run_id
            result = run_gate(
                manifest, repo_root, evidence_dir, source_commit=git_commit(repo_root)
            )
    except CompleteGateBusy:
        busy_receipt = write_busy_receipt(repo_root)
        print("Complete gate: BUSY")
        print(f"Evidence: {busy_receipt}")
        return GATE_BUSY_EXIT
    except (OSError, ValueError) as exc:
        print("Complete gate: INCOMPLETE")
        print(f"Diagnostic: gate admission or evidence validation failed: {exc}")
        return 2
    print(f"Complete gate: {result['overallStatus'].upper()}")
    print(f"Evidence: {evidence_dir / 'result.json'}")
    return {"passed": 0, "failed": 1, "incomplete": 2}[result["overallStatus"]]


if __name__ == "__main__":
    raise SystemExit(main())
