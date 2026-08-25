#!/usr/bin/env python3
"""Run the fixed Django coverage command with Coverage.py's stable C tracer."""

from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ["COVERAGE_CORE"] = "ctrace"
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "pytest",
            "django/tests",
            "-c",
            "django/pytest.ini",
            "-m",
            "not integration and not perf",
            "--cov=project",
            "--cov=users",
            "--cov=common",
            "--cov=catalog",
            "--cov=api_schema",
            "--cov-report=json:.artifacts/coverage/django.json",
        ],
    )


if __name__ == "__main__":
    main()
