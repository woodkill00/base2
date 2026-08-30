#!/usr/bin/env python3
"""Fail-closed policy for the optional Base2 live performance target."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


def evaluate(event_name: str, live_enabled: str, base_url: str) -> dict[str, str | bool]:
    if event_name == "pull_request":
        return {"enabled": False, "reason": "pull-request-hermetic", "base_url": ""}
    if live_enabled.strip().lower() != "true":
        return {"enabled": False, "reason": "live-target-not-enabled", "base_url": ""}
    value = base_url.strip().rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        return {"enabled": False, "reason": "live-target-invalid", "base_url": ""}
    return {"enabled": True, "reason": "approved-live-target", "base_url": value}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    result = evaluate(
        os.getenv("PERF_EVENT_NAME", ""),
        os.getenv("PERF_LIVE_ENABLED", ""),
        os.getenv("PERF_BASE_URL", ""),
    )
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"enabled={str(result['enabled']).lower()}\n")
            handle.write(f"reason={result['reason']}\n")
            handle.write(f"base_url={result['base_url']}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
