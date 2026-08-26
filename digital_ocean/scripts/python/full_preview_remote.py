#!/usr/bin/env python3
"""Fixed-argv, credential-safe SSH bootstrap for the complete preview stack."""
from __future__ import annotations
import hashlib
import ipaddress
import json
from pathlib import Path
import stat
import subprocess
import time
import re
from typing import Callable
from digital_ocean.scripts.python.full_preview_policy import validate_owner_cidrs
from digital_ocean.scripts.python.live_preview_provider import LivePreviewConfig

class FullPreviewRemoteError(RuntimeError):
    pass


SENSITIVE_LINE = re.compile(
    r"(?i)(password|passwd|secret|token|authorization|credential|private[_ -]?key|htpasswd)"
)
TOKEN_SHAPE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_./+=-]{32,}(?![A-Za-z0-9])")


def safe_diagnostic(stdout: str, stderr: str) -> str:
    """Return a bounded, line-filtered build diagnostic safe for operator evidence."""
    retained = []
    stage_markers = []
    for raw in (stderr + "\n" + stdout).splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("full-preview-stage-failed:"):
            stage_markers.append(line)
            continue
        if SENSITIVE_LINE.search(line):
            retained.append("[redacted sensitive diagnostic line]")
            continue
        retained.append(TOKEN_SHAPE.sub("[redacted-token]", line))
    selected = retained[-11:] + stage_markers[-1:]
    return " | ".join(selected)[:2000] or "no safe remote diagnostic"

class FullPreviewSshBootstrap:
    def __init__(self, *, known_hosts: Path, owner_cidr: str, operator_auth: Path, flower_auth: Path,
                 django_username: Path, django_email: Path, django_password: Path,
                 pgadmin_email: Path, pgadmin_password: Path,
                 runner: Callable = subprocess.run, sleep=time.sleep, attempts: int = 60):
        self.known_hosts = known_hosts
        self.owner_cidr = validate_owner_cidrs([owner_cidr])[0]
        self.operator_auth = operator_auth
        self.flower_auth = flower_auth
        self.application_inputs = (
            (django_username, "/run/base2-django.username"),
            (django_email, "/run/base2-django.email"),
            (django_password, "/run/base2-django.password"),
            (pgadmin_email, "/run/base2-pgadmin.email"),
            (pgadmin_password, "/run/base2-pgadmin.password"),
        )
        self.runner = runner
        self.sleep = sleep
        self.attempts = attempts
        if not 1 <= attempts <= 60:
            raise FullPreviewRemoteError("SSH attempts exceed bounded policy")
        for label, path in (
            ("operator auth", operator_auth), ("Flower auth", flower_auth),
            ("Django username", django_username), ("Django email", django_email),
            ("Django password", django_password), ("pgAdmin email", pgadmin_email),
            ("pgAdmin password", pgadmin_password),
        ):
            if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise FullPreviewRemoteError(f"{label} must be an owner-only real file")

    def _run(self, argv, **kwargs):
        return self.runner(argv, text=True, capture_output=True, check=False, **kwargs)

    def _options(self, config):
        return ["-i", str(config.ssh_private_key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={self.known_hosts}",
                "-o", "ConnectTimeout=5"]

    def deploy(self, ip_address: str, config: LivePreviewConfig) -> None:
        address = str(ipaddress.IPv4Address(ip_address))
        config.validate()
        if hashlib.sha256(config.source_archive.read_bytes()).hexdigest() != config.archive_sha256:
            raise FullPreviewRemoteError("source archive digest mismatch")
        self.known_hosts.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.known_hosts.touch(mode=0o600, exist_ok=True)
        self.known_hosts.chmod(0o600)
        options = self._options(config)
        target = f"root@{address}"
        for attempt in range(self.attempts):
            ready = self._run(["ssh", *options, target, "true"], timeout=15)
            if ready.returncode == 0:
                break
            if attempt + 1 == self.attempts:
                raise FullPreviewRemoteError("bounded SSH wait exhausted")
            self.sleep(5)
        copies = (
            (config.source_archive, "/tmp/base2-full-preview-source.tar"),
            (self.operator_auth, "/run/base2-operator.htpasswd"),
            (self.flower_auth, "/run/base2-flower.htpasswd"),
            *self.application_inputs,
        )
        for source, destination in copies:
            result = self._run(["scp", *options, str(source), f"{target}:{destination}"], timeout=180)
            if result.returncode != 0:
                raise FullPreviewRemoteError("private preview transfer failed")
        command = (
            "set -euo pipefail; "
            f"printf '%s  %s\\n' '{config.archive_sha256}' /tmp/base2-full-preview-source.tar | sha256sum -c - >/dev/null; "
            "rm -rf -- /opt/base2-full-preview; install -d -m 0755 /opt/base2-full-preview; "
            "tar -xf /tmp/base2-full-preview-source.tar -C /opt/base2-full-preview --no-same-owner; "
            "exec bash /opt/base2-full-preview/digital_ocean/scripts/bash/full-preview-remote.sh "
            f"'{config.zone}' '{config.droplet_name}' '{config.source_commit}' '{config.archive_sha256}' '{self.owner_cidr}'"
        )
        deployed = self._run(["ssh", *options, target, "bash", "-lc", command], timeout=1800)
        if deployed.returncode != 0:
            diagnostic = safe_diagnostic(deployed.stdout, deployed.stderr)
            raise FullPreviewRemoteError(
                f"full preview bootstrap failed (exit={deployed.returncode}): {diagnostic}"
            )
        try:
            receipt = json.loads([line for line in deployed.stdout.splitlines() if line.strip()][-1])
        except (IndexError, json.JSONDecodeError) as exc:
            raise FullPreviewRemoteError("bootstrap receipt is malformed") from exc
        if receipt.get("ok") is not True or receipt.get("mode") != "full-preview" or receipt.get("secretValuesEmitted") != 0:
            raise FullPreviewRemoteError("bootstrap receipt failed validation")

    def health(self, ip_address: str, fqdn: str) -> bool:
        address = str(ipaddress.IPv4Address(ip_address))
        result = self._run(["curl", "-ksS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "15",
                            "--resolve", f"{fqdn}:443:{address}", f"https://{fqdn}/api/health"], timeout=20)
        return result.returncode == 0 and result.stdout.strip() == "200"
