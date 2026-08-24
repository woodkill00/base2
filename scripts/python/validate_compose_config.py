#!/usr/bin/env python3
"""Validate Compose using the repository's non-secret example environment."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


PLACEHOLDER = re.compile(r"\bYOUR_[A-Z0-9_]+\b")


def render_validation_env(template: str) -> str:
    """Replace documentation placeholders with a non-secret Compose-safe value."""
    return PLACEHOLDER.sub("fixture", template)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    example = repo_root / ".env.example"
    compose = repo_root / "development.docker.yml"
    if not example.is_file() or not compose.is_file():
        print("Compose validation inputs are missing.", file=sys.stderr)
        return 1

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="base2-compose-", suffix=".env") as fixture:
        fixture.write(render_validation_env(example.read_text(encoding="utf-8")))
        fixture.flush()
        environment = os.environ.copy()
        environment["COMPOSE_ENV_FILE"] = fixture.name
        completed = subprocess.run(
            ["docker", "compose", "--env-file", fixture.name, "-f", str(compose), "config", "--quiet"],
            cwd=repo_root,
            env=environment,
            check=False,
        )
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
