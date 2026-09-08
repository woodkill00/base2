#!/usr/bin/env python3
"""Fail closed when deployment artifacts retain source-environment secrets."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SECRET_NAME = re.compile(r"(?:password|secret|token|private.?key|credential|api.?key|pepper)", re.I)
PRIVATE_MARKERS = (b"-----BEGIN PRIVATE KEY-----", b"-----BEGIN OPENSSH PRIVATE KEY-----")
MAX_FILE_BYTES = 16 * 1024 * 1024


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
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            continue
        data = path.read_bytes()
        if any(marker in data for marker in PRIVATE_MARKERS) or any(item in data for item in canaries):
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
