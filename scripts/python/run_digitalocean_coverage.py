#!/usr/bin/env python3
"""Run the fixed DigitalOcean coverage command with Coverage.py's stable C tracer."""

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
            "digital_ocean/tests",
            "--cov=digital_ocean/scripts/python",
            "--cov-report=json:.artifacts/coverage/digitalocean.json",
        ],
    )


if __name__ == "__main__":
    main()
