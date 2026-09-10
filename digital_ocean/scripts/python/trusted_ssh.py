"""Exact known-hosts policy shared by fixed deployment SSH clients."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko


def trusted_known_hosts_path() -> Path:
    raw = os.getenv("BASE2_SSH_KNOWN_HOSTS_PATH", "").strip()
    if not raw:
        raise RuntimeError("trusted_ssh_known_hosts_required")
    candidate = Path(raw).expanduser()
    if candidate.is_symlink():
        raise RuntimeError("trusted_ssh_known_hosts_symlink_rejected")
    path = candidate.resolve(strict=True)
    if not path.is_file():
        raise RuntimeError("trusted_ssh_known_hosts_not_file")
    return path


def trusted_ssh_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    try:
        client.load_host_keys(str(trusted_known_hosts_path()))
    except (OSError, ValueError, paramiko.SSHException, paramiko.hostkeys.InvalidHostKey) as exc:
        raise RuntimeError("trusted_ssh_known_hosts_invalid") from exc
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    return client


def strict_openssh_options() -> list[str]:
    return [
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={trusted_known_hosts_path()}",
    ]
