#!/usr/bin/env python3
"""Run the fixed FastAPI coverage command with Coverage.py's stable C tracer."""

from __future__ import annotations

import os
import sys


def main() -> None:
    # The Python 3.12 sys.monitoring core can emit an empty JSON report after
    # parser failures even when every test passes. The C tracer produces the
    # same line-coverage contract without that false-success failure mode.
    os.environ["COVERAGE_CORE"] = "ctrace"
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
