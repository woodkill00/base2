#!/usr/bin/env python3
"""Validate Compose using the repository's non-secret example environment."""

from __future__ import annotations

import base64
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PLACEHOLDER = re.compile(r"\bYOUR_[A-Z0-9_]+\b")


def render_validation_env(template: str) -> str:
    """Replace documentation placeholders with a non-secret Compose-safe value."""
    return PLACEHOLDER.sub("fixture", template)


def ephemeral_inspector_attestation(directory: Path) -> tuple[str, str, str]:
    """Return one valid, disposable Ed25519 seed/public pair and fixture image identity."""
    private = directory / "inspector.pem"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    private_der = subprocess.run(
        ["openssl", "pkey", "-in", str(private), "-outform", "DER"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    public_der = subprocess.run(
        ["openssl", "pkey", "-in", str(private), "-pubout", "-outform", "DER"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    private.unlink()
    if len(private_der) < 32 or len(public_der) < 32:
        raise RuntimeError("media_inspector_ephemeral_key_invalid")
    return (
        base64.urlsafe_b64encode(private_der[-32:]).decode(),
        base64.urlsafe_b64encode(public_der[-32:]).decode(),
        "base2-media-inspector:" + "0" * 64,
    )


def set_env_value(template: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    rendered, count = pattern.subn(f"{key}={value}", template)
    if count != 1:
        raise RuntimeError(f"compose_validation_key_invalid:{key}")
    return rendered


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    example = repo_root / ".env.example"
    compose = repo_root / "development.docker.yml"
    if not example.is_file() or not compose.is_file():
        print("Compose validation inputs are missing.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="base2-compose-") as temporary:
        directory = Path(temporary)
        signing, verify, identity = ephemeral_inspector_attestation(directory)
        rendered = render_validation_env(example.read_text(encoding="utf-8"))
        for key, value in (
            ("MEDIA_INSPECTOR_SIGNING_KEY", signing),
            ("MEDIA_INSPECTOR_VERIFY_KEY", verify),
            ("MEDIA_INSPECTOR_BUILD_IDENTITY", identity),
        ):
            rendered = set_env_value(rendered, key, value)
        fixture = directory / "validation.env"
        fixture.write_text(rendered, encoding="utf-8")
        fixture.chmod(0o600)
        environment = os.environ.copy()
        environment["COMPOSE_ENV_FILE"] = str(fixture)
        command = [
            "docker", "compose", "--profile", "celery", "--profile", "media-scan",
            "--env-file", str(fixture), "-f", str(compose),
        ]
        completed = subprocess.run(
            command + ["config", "--quiet"],
            cwd=repo_root,
            env=environment,
            check=False,
        )
        if completed.returncode:
            return completed.returncode
        services = subprocess.run(
            command + ["config", "--services"],
            cwd=repo_root,
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
        )
        if services.returncode:
            return services.returncode
        required = {"media-inspector", "celery-worker", "celery-beat"}
        return 0 if required <= set(services.stdout.splitlines()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
