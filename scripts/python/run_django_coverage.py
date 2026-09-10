#!/usr/bin/env python3
"""Run Django coverage with stable tracing and bounded native-crash recovery."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from stat import S_IMODE

MAX_NATIVE_ATTEMPTS = 3
NATIVE_FAILURES = {-11, 134, 139}
MAX_SHARD_BYTES = 50 * 1024 * 1024


def _parallel_shards(prefix: Path) -> set[Path]:
    return set(prefix.parent.glob(f"{prefix.name}.*"))


def _remove_failed_shards(prefix: Path, before: set[Path]) -> None:
    for shard in _parallel_shards(prefix) - before:
        if shard.is_symlink() or shard.resolve().parent != prefix.parent.resolve():
            shard.unlink(missing_ok=True)
            raise RuntimeError("django_coverage_shard_invalid")
        if not shard.is_file():
            raise RuntimeError("django_coverage_shard_invalid")
        shard.unlink()


def _validate_success_shards(prefix: Path, before: set[Path]) -> set[Path]:
    created = _parallel_shards(prefix) - before
    if len(created) != 1:
        for shard in created:
            if shard.is_symlink() or shard.is_file():
                shard.unlink(missing_ok=True)
        raise RuntimeError("django_coverage_shard_count_invalid")
    shard = next(iter(created))
    if shard.is_symlink() or shard.resolve().parent != prefix.parent.resolve():
        shard.unlink(missing_ok=True)
        raise RuntimeError("django_coverage_shard_invalid")
    if not shard.is_file():
        raise RuntimeError("django_coverage_shard_invalid")
    shard.chmod(0o600)
    stat = shard.stat()
    if S_IMODE(stat.st_mode) != 0o600 or not 0 < stat.st_size <= MAX_SHARD_BYTES:
        shard.unlink(missing_ok=True)
        raise RuntimeError("django_coverage_shard_invalid")
    return created


def _validate_complete_shards(prefix: Path, expected: set[Path]) -> None:
    actual = _parallel_shards(prefix)
    if actual != expected:
        raise RuntimeError("django_coverage_inventory_invalid")
    for shard in actual:
        if (
            shard.is_symlink()
            or shard.resolve().parent != prefix.parent.resolve()
            or not shard.is_file()
        ):
            raise RuntimeError("django_coverage_shard_invalid")
        stat = shard.stat()
        if S_IMODE(stat.st_mode) != 0o600 or not 0 < stat.st_size <= MAX_SHARD_BYTES:
            raise RuntimeError("django_coverage_shard_invalid")


def run_bounded(
    command: list[str],
    environment: dict[str, str],
    report: Path,
    parallel_prefix: Path | None = None,
    accepted_shards: set[Path] | None = None,
) -> int:
    for attempt in range(1, MAX_NATIVE_ATTEMPTS + 1):
        report.unlink(missing_ok=True)
        before = _parallel_shards(parallel_prefix) if parallel_prefix else set()
        result = subprocess.run(command, env=environment, check=False)
        if result.returncode == 0:
            if parallel_prefix:
                created = _validate_success_shards(parallel_prefix, before)
                if accepted_shards is not None:
                    accepted_shards.update(created)
            return attempt
        if parallel_prefix:
            _remove_failed_shards(parallel_prefix, before)
        if result.returncode not in NATIVE_FAILURES or attempt == MAX_NATIVE_ATTEMPTS:
            raise RuntimeError(f"django_coverage_failed:exit_{result.returncode}")
        print(
            f"Django coverage recovered from native exit {result.returncode}; "
            f"retry {attempt + 1}/{MAX_NATIVE_ATTEMPTS}",
            flush=True,
        )
    raise RuntimeError("unreachable_native_retry_state")  # pragma: no cover


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    report = root / ".artifacts/coverage/django.json"
    data = root / ".artifacts/coverage/.coverage.django"
    tests = sorted((root / "django/tests").rglob("test_*.py"))
    if not tests:
        raise RuntimeError("django_coverage_inventory_empty")
    environment = os.environ.copy()
    environment["COVERAGE_CORE"] = "sysmon"
    environment["COVERAGE_FILE"] = str(data)
    environment["PYTHONHASHSEED"] = "0"
    environment["PYTHONMALLOC"] = "malloc"
    data.unlink(missing_ok=True)
    for partition in data.parent.glob(f"{data.name}.*"):
        partition.unlink()
    retained: set[Path] = set()
    for test_file in tests:
        command = [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--source=project,users,common,catalog,api_schema",
            "-m",
            "pytest",
            str(test_file.relative_to(root)),
            "-c",
            "django/pytest.ini",
            "-o",
            "addopts=",
            "-m",
            "not integration and not perf",
            "-p",
            "no:cov",
        ]
        run_bounded(
            command,
            environment,
            report,
            parallel_prefix=data,
            accepted_shards=retained,
        )
    _validate_complete_shards(data, retained)
    if len(retained) != len(tests):
        raise RuntimeError("django_coverage_inventory_invalid")
    run_bounded(
        [sys.executable, "-m", "coverage", "combine", "--keep", str(data.parent)],
        environment,
        report,
    )
    run_bounded(
        [sys.executable, "-m", "coverage", "json", "-o", str(report)],
        environment,
        report,
    )
    for partition in data.parent.glob(f"{data.name}.*"):
        partition.unlink()


if __name__ == "__main__":
    main()
