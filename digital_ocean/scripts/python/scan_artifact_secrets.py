#!/usr/bin/env python3
"""Fail closed when deployment artifacts retain source-environment secrets."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SECRET_NAME = re.compile(r"(?:password|secret|token|private.?key|credential|api.?key|pepper)", re.I)
PRIVATE_MARKERS = (b"-----BEGIN PRIVATE KEY-----", b"-----BEGIN OPENSSH PRIVATE KEY-----")
CHUNK_BYTES = 1024 * 1024


def secret_canaries(env_path: Path) -> tuple[bytes, ...]:
    values: set[bytes] = set()
    for raw in env_path.read_text(encoding="utf-8", errors="strict").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'\"")
        if SECRET_NAME.search(key) and len(value) >= 8 and not value.startswith("${"):
            values.add(value.encode())
    return tuple(sorted(values, key=len, reverse=True))


def scan_tree(root: Path, env_path: Path) -> list[str]:
    root = root.resolve(strict=True)
    canaries = secret_canaries(env_path.resolve(strict=True))
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            findings.append(str(path.relative_to(root)))
            continue
        if not path.is_file():
            continue
        needles = (*PRIVATE_MARKERS, *canaries)
        overlap = max((len(needle) for needle in needles), default=1) - 1
        matched = False
        previous = b""
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(CHUNK_BYTES)
                if not chunk:
                    break
                window = previous + chunk
                if any(needle in window for needle in needles):
                    matched = True
                    break
                previous = window[-overlap:] if overlap else b""
        if matched:
            findings.append(str(path.relative_to(root)))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    findings = scan_tree(args.root, args.env_file)
    print(json.dumps({"status": "rejected" if findings else "passed", "findingCount": len(findings), "files": findings}, sort_keys=True))
    return 2 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
