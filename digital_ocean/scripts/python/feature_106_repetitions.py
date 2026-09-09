#!/usr/bin/env python3
"""Run and integrity-bind Feature 106 exact-head stability repetitions."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

REPETITIONS = 10
MAX_NATIVE_ATTEMPTS = 3
NATIVE_FAILURES = {-11, 134, 139}
SUITES = {
    "privacy-runtime": (
        ".venv-api/bin/python",
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        "api/tests/test_operations_runtime.py",
        "api/tests/test_runtime_governance_repository.py",
        "api/tests/test_settings_validation.py",
    ),
    "backup-release-deployment": (
        ".venv/bin/python",
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        "scripts/tests/test_production_backup.py",
        "scripts/tests/test_production_release.py",
        "scripts/tests/test_production_release_cli.py",
        "digital_ocean/tests/test_deploy_config.py",
        "digital_ocean/tests/test_deployment_evidence.py",
        "digital_ocean/tests/test_deployment_mode.py",
        "digital_ocean/tests/test_provider_lease.py",
        "digital_ocean/tests/test_provider_ready.py",
        "digital_ocean/tests/test_release_orchestrator.py",
        "digital_ocean/tests/test_validate_deployment_evidence.py",
    ),
}


class RepetitionError(RuntimeError):
    """Exact-head repetition evidence could not be produced safely."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_supported_platform() -> None:
    if os.name != "posix":
        raise RepetitionError("repetition_platform_unsupported")


def _source_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    commit = result.stdout.strip()
    if result.returncode or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RepetitionError("repetition_source_unavailable")
    return commit


def _require_clean(root: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode or result.stdout.strip():
        raise RepetitionError("repetition_source_not_clean")


def _test_environment(home: Path) -> dict[str, str]:
    """Return a hermetic child environment, never an ambient denylist."""

    environment = {
        "CI": "1",
        "ENV": "test",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_PROXY": "*",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONHASHSEED": "0",
        "PYTHONMALLOC": "malloc",
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_CONFIG_HOME": str(home / ".config"),
    }
    if os.name == "nt":
        for name in ("COMSPEC", "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP", "WINDIR"):
            value = os.environ.get(name)
            if value:
                environment[name] = value
    return environment


def _require_exact_source(root: Path, commit: str) -> None:
    if _source_commit(root) != commit:
        raise RepetitionError("repetition_source_changed")
    _require_clean(root)


@contextmanager
def _isolated_source(root: Path, commit: str, parent: Path) -> Iterator[Path]:
    """Check out one detached exact commit for the entire repetition set."""

    worktree = parent / "source"
    added = subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree), commit],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if added.returncode:
        raise RepetitionError("repetition_isolation_failed")
    try:
        _require_exact_source(worktree, commit)
        yield worktree
        _require_exact_source(worktree, commit)
    finally:
        removed = subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if removed.returncode:
            raise RepetitionError("repetition_isolation_cleanup_failed")


def _validate_existing(path: Path, commit: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise RepetitionError("repetition_evidence_invalid")
    manifest = path / "result.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise RepetitionError("repetition_evidence_invalid")
    if os.name != "nt":
        if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
            raise RepetitionError("repetition_evidence_permissions_invalid")
        if manifest.stat().st_uid != os.getuid() or manifest.stat().st_mode & 0o077:
            raise RepetitionError("repetition_evidence_permissions_invalid")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        files = payload["files"]
    except (OSError, KeyError, json.JSONDecodeError, TypeError) as exc:
        raise RepetitionError("repetition_evidence_invalid") from exc
    if (
        payload.get("schemaVersion") != 1
        or payload.get("status") != "passed"
        or payload.get("sourceCommit") != commit
        or payload.get("repetitionsPerSuite") != REPETITIONS
        or not isinstance(files, list)
        or len(files) != len(SUITES) * REPETITIONS
    ):
        raise RepetitionError("repetition_evidence_invalid")
    supplied_digest = payload.get("evidenceDigest")
    digest_payload = {key: value for key, value in payload.items() if key != "evidenceDigest"}
    expected_digest = hashlib.sha256(
        json.dumps(digest_payload, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    expected_names = {
        f"{suite}-{repetition}.log"
        for suite in SUITES
        for repetition in range(1, REPETITIONS + 1)
    }
    actual_names = {entry.name for entry in path.iterdir()}
    if (
        supplied_digest != expected_digest
        or {entry.get("name") for entry in files} != expected_names
        or actual_names != expected_names | {"result.json"}
    ):
        raise RepetitionError("repetition_evidence_invalid")
    for entry in files:
        member = path / str(entry.get("name", ""))
        if (
            not member.is_file()
            or member.is_symlink()
            or member.name != entry.get("name")
            or member.resolve().parent != path.resolve()
            or member.stat().st_size != entry.get("bytes")
            or _digest(member) != entry.get("sha256")
        ):
            raise RepetitionError("repetition_evidence_changed")
        if os.name != "nt" and (
            member.stat().st_uid != os.getuid() or member.stat().st_mode & 0o077
        ):
            raise RepetitionError("repetition_evidence_permissions_invalid")
    return manifest


def _private_evidence_root(project_root: Path) -> Path:
    artifacts = project_root / ".artifacts"
    evidence_root = artifacts / "feature-106-repetitions"
    for candidate in (artifacts, evidence_root):
        if candidate.is_symlink():
            raise RepetitionError("repetition_evidence_root_invalid")
        if candidate.exists() and not candidate.is_dir():
            raise RepetitionError("repetition_evidence_root_invalid")
        candidate.mkdir(exist_ok=True, mode=0o700)
        if os.name != "nt":
            if candidate.stat().st_uid != os.getuid():
                raise RepetitionError("repetition_evidence_permissions_invalid")
            candidate.chmod(0o700)
        if not candidate.resolve().is_relative_to(project_root):
            raise RepetitionError("repetition_evidence_root_invalid")
    return evidence_root


def _persist_failure(
    evidence_root: Path,
    commit: str,
    suite: str,
    repetition: int,
    command: tuple[str, ...],
    exit_code: int,
    output: bytes,
    attempt: int = 1,
) -> Path:
    bounded_output = output[: 1024 * 1024]
    failure_id = hashlib.sha256(
        commit.encode()
        + b"\0"
        + suite.encode()
        + b"\0"
        + str(repetition).encode()
        + b"\0"
        + str(attempt).encode()
        + b"\0"
        + bounded_output
    ).hexdigest()
    failure_parent = evidence_root / "failures" / commit
    for candidate in (evidence_root / "failures", failure_parent):
        if candidate.is_symlink() or (candidate.exists() and not candidate.is_dir()):
            raise RepetitionError("repetition_failure_evidence_invalid")
        candidate.mkdir(exist_ok=True, mode=0o700)
        if os.name != "nt":
            if candidate.stat().st_uid != os.getuid():
                raise RepetitionError("repetition_evidence_permissions_invalid")
            candidate.chmod(0o700)
        if not candidate.resolve().is_relative_to(evidence_root.resolve()):
            raise RepetitionError("repetition_failure_evidence_invalid")
    destination = failure_parent / failure_id
    payload = {
        "bytes": len(bounded_output),
        "attempt": attempt,
        "command": list(command),
        "exitCode": int(exit_code),
        "logSha256": hashlib.sha256(bounded_output).hexdigest(),
        "outputTruncated": len(output) > len(bounded_output),
        "repetition": repetition,
        "schemaVersion": 1,
        "sourceCommit": commit,
        "status": "failed",
        "suite": suite,
    }
    payload["evidenceDigest"] = hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    if destination.exists():
        manifest = destination / "result.json"
        member = destination / "failure.log"
        try:
            existing = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RepetitionError("repetition_failure_evidence_changed") from exc
        if (
            destination.is_symlink()
            or manifest.is_symlink()
            or member.is_symlink()
            or existing != payload
            or member.read_bytes() != bounded_output
            or _digest(member) != payload["logSha256"]
        ):
            raise RepetitionError("repetition_failure_evidence_changed")
        if os.name != "nt" and (
            destination.stat().st_uid != os.getuid()
            or manifest.stat().st_uid != os.getuid()
            or member.stat().st_uid != os.getuid()
            or destination.stat().st_mode & 0o077
            or manifest.stat().st_mode & 0o077
            or member.stat().st_mode & 0o077
        ):
            raise RepetitionError("repetition_evidence_permissions_invalid")
        return manifest
    with tempfile.TemporaryDirectory(prefix=f".{failure_id}.", dir=failure_parent) as raw_stage:
        stage = Path(raw_stage)
        member = stage / "failure.log"
        member.write_bytes(bounded_output)
        member.chmod(0o600)
        manifest = stage / "result.json"
        manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest.chmod(0o600)
        stage.rename(destination)
        destination.chmod(0o700)
    return destination / "result.json"


def run(root: Path | None = None) -> Path:
    _require_supported_platform()
    project_root = (root or Path(__file__).resolve().parents[3]).resolve()
    _require_clean(project_root)
    commit = _source_commit(project_root)
    evidence_root = _private_evidence_root(project_root)
    destination = evidence_root / commit
    if destination.exists():
        return _validate_existing(destination, commit)
    with tempfile.TemporaryDirectory(prefix=f".{commit}.", dir=evidence_root) as raw_stage:
        stage = Path(raw_stage)
        home = stage / "home"
        home.mkdir(mode=0o700)
        environment = _test_environment(home)
        files: list[dict[str, object]] = []
        native_crash_recoveries: list[str] = []
        with _isolated_source(project_root, commit, stage) as source:
            for suite, command in SUITES.items():
                isolated_command = (str(project_root / command[0]), *command[1:])
                for repetition in range(1, REPETITIONS + 1):
                    for attempt in range(1, MAX_NATIVE_ATTEMPTS + 1):
                        result = subprocess.run(
                            isolated_command,
                            cwd=source,
                            env=environment,
                            check=False,
                            capture_output=True,
                            text=True,
                            timeout=300,
                        )
                        _require_exact_source(source, commit)
                        _require_exact_source(project_root, commit)
                        member = stage / f"{suite}-{repetition}.log"
                        member.write_text(result.stdout + result.stderr, encoding="utf-8")
                        member.chmod(0o600)
                        if result.returncode == 0:
                            break
                        failure = _persist_failure(
                            evidence_root,
                            commit,
                            suite,
                            repetition,
                            isolated_command,
                            result.returncode,
                            member.read_bytes(),
                            attempt=attempt,
                        )
                        if (
                            result.returncode in NATIVE_FAILURES
                            and attempt < MAX_NATIVE_ATTEMPTS
                        ):
                            native_crash_recoveries.append(
                                failure.relative_to(evidence_root).as_posix()
                            )
                            continue
                        raise RepetitionError(
                            f"repetition_failed:{suite}:{repetition}:evidence={failure}"
                        )
                    files.append(
                        {
                            "bytes": member.stat().st_size,
                            "name": member.name,
                            "sha256": _digest(member),
                        }
                    )
        shutil.rmtree(home)
        payload = {
            "files": sorted(files, key=lambda entry: str(entry["name"])),
            "repetitionsPerSuite": REPETITIONS,
            "nativeCrashRecoveries": native_crash_recoveries,
            "schemaVersion": 1,
            "sourceCommit": commit,
            "status": "passed",
            "suiteCommands": {name: list(command) for name, command in sorted(SUITES.items())},
        }
        canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        payload["evidenceDigest"] = hashlib.sha256(canonical).hexdigest()
        result_path = stage / "result.json"
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result_path.chmod(0o600)
        _require_exact_source(project_root, commit)
        stage.rename(destination)
    return destination / "result.json"


def main() -> int:
    try:
        print(run())
    except (OSError, RepetitionError, subprocess.SubprocessError) as exc:
        print(f"ERROR:{type(exc).__name__}:{exc}")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the installed entrypoint
    raise SystemExit(main())
