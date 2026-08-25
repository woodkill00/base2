from __future__ import annotations

import hashlib
import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from digital_ocean.scripts.python.live_preview_provider import LivePreviewConfig
from digital_ocean.scripts.python.live_remote_bootstrap import (
    SshComposeBootstrap,
    RemoteBootstrapError,
)


def config(tmp_path: Path) -> LivePreviewConfig:
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"exact archive")
    key = tmp_path / "key"
    key.write_text("private", encoding="utf-8")
    key.chmod(0o600)
    return LivePreviewConfig(
        source_commit="a" * 40,
        plan_digest="b" * 64,
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        source_archive=archive,
        ssh_private_key=key,
        ssh_key_id=1,
        droplet_name="project1-f093-abc",
        region="nyc3",
        size="s-2vcpu-4gb",
        image="ubuntu-24-04-x64",
        zone="example.com",
        record_name="f093-abc",
        fqdn="f093-abc.example.com",
        maximum_wait_attempts=2,
        wait_interval_seconds=0,
    )


class Runner:
    def __init__(self):
        self.calls = []
        self.ssh_attempts = 0

    def __call__(self, args, **kwargs):
        self.calls.append((list(args), kwargs))
        if args[0] == "scp":
            return CompletedProcess(args, 0, "", "")
        if args[0] == "curl":
            return CompletedProcess(args, 0, "200", "")
        self.ssh_attempts += 1
        if self.ssh_attempts == 1:
            return CompletedProcess(args, 255, "", "not ready")
        if kwargs.get("input"):
            payload = {
                "ok": True,
                "sourceCommit": "a" * 40,
                "sourceArchiveSha256": hashlib.sha256(b"exact archive").hexdigest(),
                "servicesHealthy": 12,
                "certificateMode": "letsencrypt-staging-only",
                "secretValuesEmitted": 0,
            }
            return CompletedProcess(args, 0, json.dumps(payload), "")
        return CompletedProcess(args, 0, "", "")


def test_fixed_argv_bootstrap_and_health(tmp_path):
    runner = Runner()
    remote = SshComposeBootstrap(
        known_hosts=tmp_path / "known_hosts",
        runner=runner,
        sleep=lambda _delay: None,
        ssh_attempts=2,
        ssh_interval_seconds=0,
    )
    cfg = config(tmp_path)
    remote.deploy("192.0.2.42", cfg)
    assert remote.health("192.0.2.42", cfg.fqdn) is True
    flattened = [call[0] for call in runner.calls]
    assert any(args[0] == "scp" and str(cfg.source_archive) in args for args in flattened)
    bootstrap_call = next(call for call in runner.calls if call[1].get("input"))
    assert bootstrap_call[0][0] == "ssh"
    assert "StrictHostKeyChecking=accept-new" in bootstrap_call[0]
    assert cfg.archive_sha256 in bootstrap_call[0]
    assert "rm -rf -- /opt/base2-feature093-canary" in bootstrap_call[1]["input"]
    curl = flattened[-1]
    assert curl[:2] == ["curl", "--silent"]
    assert "--resolve" in curl and "-k" in curl


def test_archive_tamper_fails_before_network(tmp_path):
    runner = Runner()
    cfg = config(tmp_path)
    cfg.source_archive.write_bytes(b"changed")
    remote = SshComposeBootstrap(known_hosts=tmp_path / "known", runner=runner)
    with pytest.raises(RemoteBootstrapError, match="archive digest"):
        remote.deploy("192.0.2.42", cfg)
    assert runner.calls == []


def test_host_and_remote_receipt_mismatch_fail_closed(tmp_path):
    runner = Runner()
    remote = SshComposeBootstrap(known_hosts=tmp_path / "known", runner=runner)
    with pytest.raises(RemoteBootstrapError, match="IPv4"):
        remote.deploy("not-an-ip", config(tmp_path))

    class Bad(Runner):
        def __call__(self, args, **kwargs):
            result = super().__call__(args, **kwargs)
            if kwargs.get("input") and result.returncode == 0:
                payload = json.loads(result.stdout)
                payload["sourceCommit"] = "c" * 40
                return CompletedProcess(args, 0, json.dumps(payload), "")
            return result

    bad = Bad()
    remote = SshComposeBootstrap(
        known_hosts=tmp_path / "known2", runner=bad, sleep=lambda _delay: None
    )
    with pytest.raises(RemoteBootstrapError, match="identity"):
        remote.deploy("192.0.2.42", config(tmp_path))
