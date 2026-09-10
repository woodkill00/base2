#!/usr/bin/env python3
"""Run Django coverage with stable tracing and bounded native-crash recovery."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

MAX_NATIVE_ATTEMPTS = 3
NATIVE_FAILURES = {-11, 134, 139}


def run_bounded(command: list[str], environment: dict[str, str], report: Path) -> int:
    for attempt in range(1, MAX_NATIVE_ATTEMPTS + 1):
        report.unlink(missing_ok=True)
        result = subprocess.run(command, env=environment, check=False)
        if result.returncode == 0:
            return attempt
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
        run_bounded(command, environment, report)
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
