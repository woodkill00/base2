#!/usr/bin/env python3
"""Run and retain private, integrity-bound isolated-E2E concurrency evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import select
import stat
import subprocess
import sys
import tempfile
import uuid
from contextlib import suppress
from pathlib import Path

try:
    from scripts.python.run_complete_gate import open_private_directory, open_private_file
except ModuleNotFoundError:  # Direct repository script execution.
    from run_complete_gate import open_private_directory, open_private_file

MAX_LOG_BYTES = 1024 * 1024
OWNER_TIMEOUT = 900


class EvidenceError(RuntimeError):
    pass


def _commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise EvidenceError("e2e_concurrency_source_invalid")
    if status.returncode or status.stdout:
        raise EvidenceError("e2e_concurrency_source_not_clean")
    return value


def _read_private_member(directory_fd: int, name: str) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory_fd)
    try:
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or details.st_uid != os.geteuid()
            or details.st_nlink != 1
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_size > MAX_LOG_BYTES
        ):
            raise EvidenceError("e2e_concurrency_evidence_permissions_invalid")
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            return stream.read(MAX_LOG_BYTES + 1)
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, value: bytes) -> None:
    view = memoryview(value)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise EvidenceError("e2e_concurrency_evidence_write_failed")
        view = view[written:]


def _validate_fd(evidence_fd: int, commit: str) -> str:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    destination_fd = os.open(commit, flags, dir_fd=evidence_fd)
    try:
        details = os.fstat(destination_fd)
        if details.st_uid != os.geteuid() or stat.S_IMODE(details.st_mode) != 0o700:
            raise EvidenceError("e2e_concurrency_evidence_permissions_invalid")
        if set(os.listdir(destination_fd)) != {"owner.log", "contender.log", "result.json"}:
            raise EvidenceError("e2e_concurrency_evidence_invalid")
        members = {
            name: _read_private_member(destination_fd, name)
            for name in ("owner.log", "contender.log", "result.json")
        }
        payload = json.loads(members["result.json"].decode("utf-8"))
        files = payload.get("files")
        unsigned = {key: value for key, value in payload.items() if key != "evidenceDigest"}
        expected = hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if (
            payload.get("schemaVersion") != 1
            or payload.get("status") != "passed"
            or payload.get("sourceCommit") != commit
            or payload.get("ownerExitCode") != 0
            or payload.get("contenderExitCode") != 3
            or payload.get("finalInventory") != "empty"
            or payload.get("evidenceDigest") != expected
            or not isinstance(files, list)
            or {item.get("name") for item in files} != {"owner.log", "contender.log"}
        ):
            raise EvidenceError("e2e_concurrency_evidence_invalid")
        for item in files:
            value = members[item["name"]]
            if len(value) != item.get("bytes") or hashlib.sha256(value).hexdigest() != item.get("sha256"):
                raise EvidenceError("e2e_concurrency_evidence_changed")
    finally:
        os.close(destination_fd)
    return f".artifacts/feature-106-e2e-concurrency/{commit}/result.json"


def _persist_verified(logs: dict[str, bytes], commit: str, root: Path) -> Path:
    if set(logs) != {"owner.log", "contender.log"} or any(
        len(value) > MAX_LOG_BYTES for value in logs.values()
    ):
        raise EvidenceError("e2e_concurrency_log_invalid")
    if b"4 passed" not in logs["owner.log"] or b"fixed isolated E2E project is already in use" not in logs["contender.log"]:
        raise EvidenceError("e2e_concurrency_result_invalid")
    evidence_path = root / ".artifacts" / "feature-106-e2e-concurrency"
    try:
        evidence_fd = open_private_directory(evidence_path, root)
    except (OSError, ValueError) as exc:
        raise EvidenceError("e2e_concurrency_evidence_root_unsafe") from exc
    stage_name = f".{commit}.{uuid.uuid4().hex}"
    stage_fd: int | None = None
    try:
        if commit in os.listdir(evidence_fd):
            return root / _validate_fd(evidence_fd, commit)
        os.mkdir(stage_name, 0o700, dir_fd=evidence_fd)
        stage_fd = os.open(
            stage_name, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=evidence_fd,
        )
        files = []
        for name, value in sorted(logs.items()):
            member_fd = open_private_file(stage_fd, name)
            try:
                _write_all(member_fd, value)
                os.fsync(member_fd)
            finally:
                os.close(member_fd)
            files.append({"name": name, "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()})
        payload = {
            "schemaVersion": 1, "status": "passed", "sourceCommit": commit,
            "ownerExitCode": 0, "contenderExitCode": 3, "finalInventory": "empty",
            "files": files,
        }
        payload["evidenceDigest"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
        manifest_fd = open_private_file(stage_fd, "result.json")
        try:
            _write_all(manifest_fd, encoded)
            os.fsync(manifest_fd)
        finally:
            os.close(manifest_fd)
        os.close(stage_fd)
        stage_fd = None
        os.rename(stage_name, commit, src_dir_fd=evidence_fd, dst_dir_fd=evidence_fd)
        return root / _validate_fd(evidence_fd, commit)
    finally:
        if stage_fd is not None:
            os.close(stage_fd)
        with suppress(OSError):
            cleanup_fd = os.open(
                stage_name, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=evidence_fd,
            )
            try:
                for name in os.listdir(cleanup_fd):
                    os.unlink(name, dir_fd=cleanup_fd)
            finally:
                os.close(cleanup_fd)
            os.rmdir(stage_name, dir_fd=evidence_fd)
        os.close(evidence_fd)


def _inventory_empty() -> bool:
    commands = (
        (["docker", "ps", "-a", "--format", "{{.Names}}"], "base2-e2e-isolated-"),
        (["docker", "volume", "ls", "--format", "{{.Name}}"], "base2-e2e-isolated_"),
        (["docker", "network", "ls", "--format", "{{.Name}}"], "base2-e2e-isolated_"),
    )
    for command, prefix in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
        if result.returncode or any(line.startswith(prefix) for line in result.stdout.splitlines()):
            return False
    return True


def run_and_record(root: Path | None = None) -> Path:
    project_root = (root or Path(__file__).resolve().parents[2]).resolve()
    commit = _commit(project_root)
    runner = project_root / "scripts" / "bash" / "e2e-isolated.sh"
    owner: subprocess.Popen[bytes] | None = None
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    try:
        with tempfile.TemporaryDirectory(prefix="base2-feature-106-concurrency.") as raw:
            temporary = Path(raw)
            temporary.chmod(0o700)
            owner_path = temporary / "owner.log"
            contender_path = temporary / "contender.log"
            with owner_path.open("wb") as owner_stream:
                environment = dict(os.environ)
                environment["E2E_READY_FD"] = str(write_fd)
                owner = subprocess.Popen(
                    [str(runner)], cwd=project_root, env=environment, stdout=owner_stream,
                    stderr=subprocess.STDOUT, pass_fds=(write_fd,),
                )
                os.close(write_fd)
                write_fd = -1
                ready, _, _ = select.select([read_fd], [], [], 20)
                marker = os.read(read_fd, 16) if ready else b""
                if marker != b"ready\n":
                    raise EvidenceError("e2e_concurrency_owner_not_ready")
                with contender_path.open("wb") as contender_stream:
                    contender = subprocess.run(
                        [str(runner)], cwd=project_root, stdout=contender_stream,
                        stderr=subprocess.STDOUT, check=False, timeout=60,
                    )
                owner_code = owner.wait(timeout=OWNER_TIMEOUT)
            if owner_code != 0 or contender.returncode != 3 or not _inventory_empty():
                raise EvidenceError("e2e_concurrency_observed_result_invalid")
            if _commit(project_root) != commit:
                raise EvidenceError("e2e_concurrency_source_changed")
            logs = {"owner.log": owner_path.read_bytes(), "contender.log": contender_path.read_bytes()}
            return _persist_verified(logs, commit, project_root)
    finally:
        if write_fd >= 0:
            os.close(write_fd)
        os.close(read_fd)
        if owner is not None and owner.poll() is None:
            owner.terminate()
            with suppress(subprocess.TimeoutExpired):
                owner.wait(timeout=10)
            if owner.poll() is None:
                owner.kill()
                owner.wait()


def main(argv: list[str]) -> int:
    if argv:
        print("ERROR:e2e_concurrency_arguments_invalid")
        return 2
    try:
        print(run_and_record())
    except (EvidenceError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"ERROR:{type(exc).__name__}:{exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
