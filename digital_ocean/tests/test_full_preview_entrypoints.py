from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from digital_ocean.scripts.python import full_preview_cli, full_preview_expire, full_preview_live
from digital_ocean.scripts.python.full_preview_expire import ExpiryError, LeaseDigitalOceanProvider
from digital_ocean.scripts.python.full_preview_remote import (
    FullPreviewRemoteError,
    FullPreviewSshBootstrap,
    safe_diagnostic,
)
from digital_ocean.scripts.python.live_preview_provider import LivePreviewConfig


def private_file(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def remote_config(tmp_path: Path) -> LivePreviewConfig:
    archive = private_file(tmp_path / "source.tar", "archive")
    key = private_file(tmp_path / "id_ed25519", "key")
    return LivePreviewConfig(
        source_commit="a" * 40,
        plan_digest="b" * 64,
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        source_archive=archive,
        ssh_private_key=key,
        ssh_key_id=77,
        droplet_name="base2-full-preview",
        region="fra1",
        size="s-2vcpu-2gb",
        image="ubuntu-24-04-x64",
        zone="woodkilldev.com",
        record_name="admin",
        fqdn="admin.woodkilldev.com",
        admission_tag="base2-full-20260826-001",
    )


def test_cli_policy_and_probe_entrypoints(tmp_path, monkeypatch, capsys):
    assert full_preview_cli.main(
        ["policy", "--domain", "woodkilldev.com", "--owner-cidr", "8.8.8.8/32"]
    ) == 0
    policy = json.loads(capsys.readouterr().out)
    assert policy["status"] == "ready_for_live_approval"
    assert len(policy["policyDigest"]) == 64

    username = private_file(tmp_path / "username", "owner")
    password = private_file(tmp_path / "password", "secret")
    monkeypatch.setattr(
        full_preview_cli,
        "verify_full_preview",
        lambda *args, **kwargs: {"ok": True, "routeCount": 8},
    )
    assert full_preview_cli.main(
        [
            "probe",
            "--domain",
            "woodkilldev.com",
            "--ip-address",
            "8.8.8.8",
            "--owner-cidr",
            "8.8.4.4/32",
            "--username-file",
            str(username),
            "--password-file",
            str(password),
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["routeCount"] == 8

    password.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"):
        full_preview_cli._private_text(password, "password")


def test_expiry_token_provider_and_main(tmp_path, monkeypatch, capsys):
    credential = private_file(
        tmp_path / "credential.json", json.dumps({"secrets": {"DO_API_TOKEN": "token"}})
    )
    assert full_preview_expire._token(credential) == "token"
    private_file(credential, json.dumps({"secrets": {}}))
    with pytest.raises(ExpiryError, match="unavailable"):
        full_preview_expire._token(credential)
    credential.chmod(0o644)
    with pytest.raises(ExpiryError, match="owner-only"):
        full_preview_expire._token(credential)

    class NotFound(Exception):
        status_code = 404

    class Droplets:
        def __init__(self):
            self.deleted = []

        def get(self, resource_id):
            if resource_id == 404:
                raise NotFound()
            return {
                "droplet": {
                    "id": resource_id,
                    "name": "preview",
                    "tags": ["z", "a"],
                    "size": {"slug": "s-2vcpu-2gb"},
                    "created_at": "now",
                }
            }

        def delete(self, resource_id):
            self.deleted.append(resource_id)

        def list(self, tag_name=None):
            return {"droplets": [self.get(7)["droplet"]]}

    class Domains:
        def __init__(self):
            self.deleted = []

        def list_records(self, domain):
            return {"domain_records": [{"id": 9, "type": "A", "name": "@", "data": "8.8.8.8"}]}

        def delete_record(self, domain, record_id):
            self.deleted.append((domain, record_id))

    client = SimpleNamespace(droplets=Droplets(), domains=Domains())
    provider = LeaseDigitalOceanProvider(client)
    assert provider.get_droplet("7")["tags"] == ["a", "z"]
    assert provider.get_droplet("404") is None
    assert provider.list_owned_droplets("run")[0]["id"] == "7"
    provider.delete_droplet("7")
    assert client.droplets.deleted == [7]
    assert provider.get_dns_record("woodkilldev.com", "9")["state"] == "bound"
    assert provider.get_dns_record("woodkilldev.com", "10") is None
    provider.delete_dns_record("woodkilldev.com", "9")
    assert client.domains.deleted == [("woodkilldev.com", 9)]

    credential.chmod(0o600)
    private_file(credential, json.dumps({"secrets": {"DO_API_TOKEN": "token"}}))
    monkeypatch.setattr(full_preview_expire, "DigitalOceanHttpClient", lambda token: client)
    monkeypatch.setattr(
        full_preview_expire,
        "teardown_full_preview",
        lambda *args, **kwargs: {
            "state": "destroyed",
            "runId": "base2-full-20260826-001",
            "mutationCounts": {"dropletsDeleted": 1, "dnsRecordsDeleted": 6},
        },
    )
    assert full_preview_expire.main(
        [
            "--state-root",
            str(tmp_path / "state"),
            "--run-id",
            "base2-full-20260826-001",
            "--credential-file",
            str(credential),
            "--early-approved",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_remote_bootstrap_deploy_health_and_failures(tmp_path):
    operator = private_file(tmp_path / "operator", "owner:$apr1$abc$hash")
    flower = private_file(tmp_path / "flower", "flower:$apr1$def$hash")
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if argv[0] == "ssh" and argv[-1] == "true" and sum(1 for row in calls if row[-1] == "true") == 1:
            return SimpleNamespace(returncode=1, stdout="", stderr="waiting")
        if argv[0] == "ssh" and "bash" in argv:
            return SimpleNamespace(
                returncode=0,
                stdout='noise\n{"ok":true,"mode":"full-preview","secretValuesEmitted":0}\n',
                stderr="",
            )
        if argv[0] == "curl":
            return SimpleNamespace(returncode=0, stdout="200", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    remote = FullPreviewSshBootstrap(
        known_hosts=tmp_path / "ssh" / "known_hosts",
        owner_cidr="8.8.4.4/32",
        operator_auth=operator,
        flower_auth=flower,
        runner=runner,
        sleep=lambda _: None,
        attempts=2,
    )
    config = remote_config(tmp_path)
    remote.deploy("8.8.8.8", config)
    assert remote.health("8.8.8.8", "woodkilldev.com") is True
    assert sum(1 for call in calls if call[0] == "scp") == 3
    assert (tmp_path / "ssh" / "known_hosts").stat().st_mode & 0o777 == 0o600

    with pytest.raises(FullPreviewRemoteError, match="digest"):
        remote.deploy("8.8.8.8", replace(config, archive_sha256="0" * 64))
    with pytest.raises(FullPreviewRemoteError, match="attempts"):
        FullPreviewSshBootstrap(
            known_hosts=tmp_path / "known2",
            owner_cidr="8.8.4.4/32",
            operator_auth=operator,
            flower_auth=flower,
            attempts=0,
        )


def test_remote_bootstrap_failure_retains_only_bounded_redacted_diagnostics(tmp_path):
    operator = private_file(tmp_path / "operator", "owner:$apr1$abc$hash")
    flower = private_file(tmp_path / "flower", "flower:$apr1$def$hash")

    def runner(argv, **kwargs):
        if argv[0] == "ssh" and argv[-1] == "true":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if argv[0] == "scp":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(
            returncode=17,
            stdout="build stage api failed\nTOKEN=abcdefghijklmnopqrstuvwxyz0123456789\n",
            stderr="password=never-print\nexecutor returned non-zero\n",
        )

    remote = FullPreviewSshBootstrap(
        known_hosts=tmp_path / "known_hosts",
        owner_cidr="8.8.4.4/32",
        operator_auth=operator,
        flower_auth=flower,
        runner=runner,
        attempts=1,
    )
    with pytest.raises(FullPreviewRemoteError, match="exit=17") as failure:
        remote.deploy("8.8.8.8", remote_config(tmp_path))
    message = str(failure.value)
    assert "executor returned non-zero" in message
    assert "never-print" not in message
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in message
    assert "[redacted" in message

    bounded = safe_diagnostic("\n".join(f"safe line {index}" for index in range(20)), "")
    assert "safe line 8" in bounded and "safe line 7" not in bounded


def test_live_main_constructs_exact_dependencies(tmp_path, monkeypatch, capsys):
    credential = private_file(
        tmp_path / "credential.json", json.dumps({"secrets": {"DO_API_TOKEN": "token"}})
    )
    archive = private_file(tmp_path / "source.tar", "archive")
    key = private_file(tmp_path / "key", "key")
    operator = private_file(tmp_path / "operator", "operator")
    flower = private_file(tmp_path / "flower", "flower")
    username = private_file(tmp_path / "username", "owner")
    password = private_file(tmp_path / "password", "secret")
    client = object()
    remote = object()
    monkeypatch.setattr(full_preview_live, "DigitalOceanHttpClient", lambda token: client)
    monkeypatch.setattr(full_preview_live, "FullPreviewSshBootstrap", lambda **kwargs: remote)

    def fake_launch(**kwargs):
        assert kwargs["client"] is client and kwargs["remote"] is remote
        assert kwargs["probe_username"] == "owner"
        return {"ok": True, "status": "live-verified"}

    monkeypatch.setattr(full_preview_live, "launch", fake_launch)
    assert full_preview_live.main(
        [
            "--credential-file", str(credential),
            "--source-archive", str(archive),
            "--ssh-private-key", str(key),
            "--ssh-key-id", "77",
            "--operator-auth-file", str(operator),
            "--flower-auth-file", str(flower),
            "--probe-username-file", str(username),
            "--probe-password-file", str(password),
            "--source-commit", "a" * 40,
            "--profile-digest", "b" * 64,
            "--domain", "woodkilldev.com",
            "--owner-cidr", "8.8.4.4/32",
            "--run-id", "base2-full-20260826-001",
            "--state-root", str(tmp_path / "state"),
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "live-verified"


def test_live_private_helpers_and_cleanup_reconciliation(tmp_path):
    secret = private_file(tmp_path / "secret", "value")
    assert full_preview_live._private(secret, "secret") == "value"
    secret.write_text("", encoding="utf-8")
    with pytest.raises(full_preview_live.FullPreviewLaunchError, match="empty"):
        full_preview_live._private(secret, "secret")
    receipt = tmp_path / "receipt.json"
    full_preview_live._write(receipt, {"ok": True})
    assert json.loads(receipt.read_text())["ok"] is True
    assert receipt.stat().st_mode & 0o777 == 0o600
