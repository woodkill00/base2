#!/usr/bin/env python3
"""Run the fixed FastAPI coverage command with Python 3.12 sys.monitoring."""

from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ["COVERAGE_CORE"] = "sysmon"
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "pytest",
            "api/tests",
            "-c",
            "api/pytest.ini",
            "-m",
            "not integration and not perf",
            "--cov-report=json:.artifacts/coverage/api.json",
        ],
    )


if __name__ == "__main__":
    main()
