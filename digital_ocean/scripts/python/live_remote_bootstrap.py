#!/usr/bin/env python3
"""Fixed-argv SSH deployment for an exact Feature 093 source archive."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Callable

from digital_ocean.scripts.python.live_preview_provider import LivePreviewConfig


class RemoteBootstrapError(RuntimeError):
    pass


REMOTE_BOOTSTRAP = r"""set -euo pipefail
archive=/tmp/base2-feature093-source.tar
root=/opt/base2-feature093-canary
fqdn="$1"
project="$2"
source_commit="$3"
archive_sha256="$4"
printf '%s  %s\n' "$archive_sha256" "$archive" | sha256sum -c - >/dev/null
rm -rf -- /opt/base2-feature093-canary
install -d -m 0755 "$root"
tar --extract --file "$archive" --directory "$root" --no-same-owner
exec bash "$root/digital_ocean/scripts/bash/live-canary-remote.sh" \
  "$fqdn" "$project" "$source_commit" "$archive_sha256"
"""


class SshComposeBootstrap:
    def __init__(
        self,
        *,
        known_hosts: Path,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        sleep=time.sleep,
        ssh_attempts: int = 60,
        ssh_interval_seconds: float = 5.0,
    ) -> None:
        if not 1 <= ssh_attempts <= 60 or not 0 <= ssh_interval_seconds <= 15:
            raise ValueError("SSH wait policy is outside bounded limits")
        self.known_hosts = known_hosts
        self.runner = runner
        self.sleep = sleep
        self.ssh_attempts = ssh_attempts
        self.ssh_interval_seconds = ssh_interval_seconds

    @staticmethod
    def _ip(value: str) -> str:
        try:
            return str(ipaddress.IPv4Address(value))
        except ipaddress.AddressValueError as exc:
            raise RemoteBootstrapError("exact public IPv4 address is required") from exc

    def _prepare_known_hosts(self) -> None:
        self.known_hosts.parent.mkdir(parents=True, exist_ok=True)
        self.known_hosts.parent.chmod(0o700)
        if not self.known_hosts.exists():
            self.known_hosts.touch(mode=0o600)
        self.known_hosts.chmod(0o600)

    def _ssh_options(self, config: LivePreviewConfig) -> list[str]:
        return [
            "-i",
            str(config.ssh_private_key),
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"UserKnownHostsFile={self.known_hosts}",
            "-o",
            "ConnectTimeout=5",
        ]

    def _run(self, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return self.runner(
            args,
            text=True,
            capture_output=True,
            timeout=kwargs.pop("timeout", 60),
            check=False,
            **kwargs,
        )

    def deploy(self, ip_address: str, config: LivePreviewConfig) -> None:
        address = self._ip(ip_address)
        config.validate()
        actual_digest = hashlib.sha256(config.source_archive.read_bytes()).hexdigest()
        if actual_digest != config.archive_sha256:
            raise RemoteBootstrapError("source archive digest differs from approved plan")
        self._prepare_known_hosts()
        options = self._ssh_options(config)
        target = f"root@{address}"

        for attempt in range(self.ssh_attempts):
            ready = self._run(["ssh", *options, target, "true"], timeout=15)
            if ready.returncode == 0:
                break
            if attempt + 1 == self.ssh_attempts:
                raise RemoteBootstrapError("bounded SSH readiness wait exhausted")
            self.sleep(self.ssh_interval_seconds)

        copied = self._run(
            [
                "scp",
                *options,
                str(config.source_archive),
                f"{target}:/tmp/base2-feature093-source.tar",
            ],
            timeout=180,
        )
        if copied.returncode != 0:
            raise RemoteBootstrapError("exact source archive transfer failed")

        deployed = self._run(
            [
                "ssh",
                *options,
                target,
                "bash",
                "-s",
                "--",
                config.fqdn,
                config.droplet_name,
                config.source_commit,
                config.archive_sha256,
            ],
            input=REMOTE_BOOTSTRAP,
            timeout=840,
        )
        if deployed.returncode != 0:
            raise RemoteBootstrapError("remote Compose bootstrap failed")
        lines = [line for line in deployed.stdout.splitlines() if line.strip()]
        try:
            receipt = json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            raise RemoteBootstrapError("remote bootstrap receipt is malformed") from exc
        expected = {
            "ok": True,
            "sourceCommit": config.source_commit,
            "sourceArchiveSha256": config.archive_sha256,
            "certificateMode": "letsencrypt-staging-only",
            "secretValuesEmitted": 0,
        }
        if any(receipt.get(key) != value for key, value in expected.items()) or int(
            receipt.get("servicesHealthy", 0)
        ) < 1:
            raise RemoteBootstrapError("remote bootstrap identity receipt does not match")

    def health(self, ip_address: str, fqdn: str) -> bool:
        address = self._ip(ip_address)
        if not fqdn or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-." for character in fqdn):
            raise RemoteBootstrapError("health hostname is unsafe")
        result = self._run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--output",
                "/dev/null",
                "--write-out",
                "%{http_code}",
                "--connect-timeout",
                "5",
                "--max-time",
                "15",
                "--resolve",
                f"{fqdn}:443:{address}",
                "-k",
                f"https://{fqdn}/api/health",
            ],
            timeout=20,
        )
        return result.returncode == 0 and result.stdout.strip() == "200"
