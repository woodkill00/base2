from pathlib import Path

import paramiko
import pytest

from digital_ocean.scripts.python.trusted_ssh import (
    strict_openssh_options,
    trusted_known_hosts_path,
    trusted_ssh_client,
)


def _known_hosts(path: Path) -> Path:
    hosts = paramiko.HostKeys()
    hosts.add("192.0.2.10", "ssh-rsa", paramiko.RSAKey.generate(1024))
    hosts.save(path)
    return path


def test_trusted_ssh_policy_loads_exact_hosts_and_rejects_unknown(monkeypatch, tmp_path):
    path = _known_hosts(tmp_path / "known_hosts")
    monkeypatch.setenv("BASE2_SSH_KNOWN_HOSTS_PATH", str(path))
    assert trusted_known_hosts_path() == path
    client = trusted_ssh_client()
    assert isinstance(client._policy, paramiko.RejectPolicy)
    assert client.get_host_keys().lookup("192.0.2.10") is not None
    assert strict_openssh_options() == [
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={path}",
    ]


def test_trusted_ssh_policy_rejects_missing_and_symlinked_inventory(monkeypatch, tmp_path):
    monkeypatch.delenv("BASE2_SSH_KNOWN_HOSTS_PATH", raising=False)
    with pytest.raises(RuntimeError, match="known_hosts_required"):
        trusted_known_hosts_path()
    target = _known_hosts(tmp_path / "target")
    link = tmp_path / "known_hosts"
    link.symlink_to(target)
    monkeypatch.setenv("BASE2_SSH_KNOWN_HOSTS_PATH", str(link))
    with pytest.raises(RuntimeError, match="symlink_rejected"):
        trusted_known_hosts_path()


def test_trusted_ssh_policy_rejects_non_file_inventory(monkeypatch, tmp_path):
    monkeypatch.setenv("BASE2_SSH_KNOWN_HOSTS_PATH", str(tmp_path))
    with pytest.raises(RuntimeError, match="not_file"):
        trusted_known_hosts_path()


def test_trusted_ssh_policy_rejects_malformed_inventory(monkeypatch, tmp_path):
    path = tmp_path / "known_hosts"
    path.write_text("not a known-hosts record\n", encoding="utf-8")
    monkeypatch.setenv("BASE2_SSH_KNOWN_HOSTS_PATH", str(path))
    with pytest.raises(RuntimeError, match="known_hosts_invalid"):
        trusted_ssh_client()
