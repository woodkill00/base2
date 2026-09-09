#!/usr/bin/env python3
"""Remove basic-auth verifier values from Traefik YAML evidence."""

from __future__ import annotations

import sys


def sanitize(text: str) -> str:
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    basic_indent: int | None = None
    users_indent: int | None = None

    for line in lines:
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)

        if basic_indent is not None and stripped.strip() and indent <= basic_indent:
            basic_indent = None
            users_indent = None

        if stripped.startswith("basicAuth:"):
            basic_indent = indent
            users_indent = None
            output.append(line)
            continue

        if basic_indent is not None and stripped.startswith("users:"):
            users_indent = indent
            newline = "\n" if line.endswith("\n") else ""
            output.append(f"{' ' * indent}users: ['REDACTED']{newline}")
            continue

        if users_indent is not None and indent > users_indent:
            continue

        output.append(line)

    return "".join(output)


def main() -> int:
    sys.stdout.write(sanitize(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
