from __future__ import annotations

from dataclasses import replace

import pytest

from digital_ocean.scripts.python.live_preview_provider import (
    LiveDigitalOceanProvider,
    LivePreviewConfig,
    LiveProviderError,
)


class Droplets:
    def __init__(self):
        self.rows = {}
        self.created = []
        self.deleted = []

    def create(self, payload):
        self.created.append(payload)
        row = {
            "id": 42,
            "name": payload["name"],
            "status": "active",
            "tags": list(payload["tags"]),
            "networks": {"v4": [{"type": "public", "ip_address": "192.0.2.42"}]},
        }
        self.rows[42] = row
        return {"droplet": row}

    def get(self, provider_id):
        if int(provider_id) not in self.rows:
            error = RuntimeError("missing")
            error.status_code = 404
            raise error
        return {"droplet": self.rows[int(provider_id)]}

    def list(self, tag_name=None):
        rows = list(self.rows.values())
        if tag_name:
            rows = [row for row in rows if tag_name in row["tags"]]
        return {"droplets": rows}

    def delete(self, provider_id):
        self.deleted.append(int(provider_id))
        self.rows.pop(int(provider_id), None)


class Domains:
    def __init__(self):
        self.records = []
        self.calls = []
        self.next_id = 1

    def list_records(self, zone):
        self.calls.append(("list", zone))
        return {"domain_records": list(self.records)}

    def create_record(self, zone, payload):
        self.calls.append(("create", zone, payload.copy()))
        row = {"id": self.next_id, **payload}
        self.next_id += 1
        self.records.append(row)
        return {"domain_record": row}

    def update_record(self, zone, record_id, payload):
        self.calls.append(("update", zone, record_id, payload.copy()))
        row = next(item for item in self.records if item["id"] == record_id)
        row.update(payload)
        return {"domain_record": row}

    def delete_record(self, zone, record_id):
        self.calls.append(("delete", zone, record_id))
        self.records = [item for item in self.records if item["id"] != record_id]


class Client:
    def __init__(self):
        self.droplets = Droplets()
        self.domains = Domains()


class Remote:
    def __init__(self):
        self.deploys = []
        self.healthy = True

    def deploy(self, ip_address, config):
        self.deploys.append((ip_address, config.source_commit, config.fqdn))

    def health(self, ip_address, fqdn):
        return self.healthy and ip_address == "192.0.2.42" and fqdn == "f093-abc.example.com"


@pytest.fixture
def config(tmp_path):
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"archive")
    key = tmp_path / "key"
    key.write_text("private", encoding="utf-8")
    key.chmod(0o600)
    return LivePreviewConfig(
        source_commit="a" * 40,
        plan_digest="b" * 64,
        archive_sha256="72e2f3a45997889d01874c9f1f6a3f9c14b6f56c6a33137c4d4f6f6f0f4f5f70",
        source_archive=archive,
        ssh_private_key=key,
        ssh_key_id=57087360,
        droplet_name="project1-f093-abc",
        region="nyc3",
        size="s-2vcpu-4gb",
        image="ubuntu-24-04-x64",
        zone="example.com",
        record_name="f093-abc",
        fqdn="f093-abc.example.com",
        maximum_wait_attempts=2,
    )


def test_provision_bootstrap_health_and_exact_owned_delete(config):
    client, remote = Client(), Remote()
    provider = LiveDigitalOceanProvider(client, config, remote, sleep=lambda _delay: None)
    row = provider.provision("base2-f093-owned")
    assert row["id"] == 42
    assert client.droplets.created == [
        {
            "name": "project1-f093-abc",
            "region": "nyc3",
            "size": "s-2vcpu-4gb",
            "image": "ubuntu-24-04-x64",
            "ssh_keys": [57087360],
            "backups": False,
            "ipv6": False,
            "monitoring": False,
            "tags": ["base2-f093-owned"],
        }
    ]
    provider.bootstrap("42")
    assert remote.deploys == [("192.0.2.42", "a" * 40, "f093-abc.example.com")]
    assert provider.health("42") is True
    assert provider.get_resource("digitalocean", "droplet", "42")["id"] == 42
    assert provider.list_owned_resources("base2-f093-owned")[0]["id"] == 42
    provider.delete_resource("digitalocean", "droplet", "42")
    assert provider.get_resource("digitalocean", "droplet", "42") is None


def test_exact_owned_replay_reconciles_without_second_create(config):
    client, remote = Client(), Remote()
    provider = LiveDigitalOceanProvider(client, config, remote, sleep=lambda _delay: None)
    provider.provision("base2-f093-owned")
    assert provider.provision("base2-f093-owned")["id"] == 42
    with pytest.raises(LiveProviderError, match="provider/kind"):
        provider.get_resource("other", "droplet", "42")
    assert len(client.droplets.created) == 1


def test_dns_is_restricted_to_one_exact_record_and_restores_absence(config):
    client, remote = Client(), Remote()
    provider = LiveDigitalOceanProvider(client, config, remote, sleep=lambda _delay: None)
    assert provider.read_values("example.com", "f093-abc", "A") == []
    provider.replace_values("example.com", "f093-abc", "A", ["192.0.2.42"])
    assert provider.read_values("example.com", "f093-abc", "A") == ["192.0.2.42"]
    provider.replace_values("example.com", "f093-abc", "A", [])
    assert provider.read_values("example.com", "f093-abc", "A") == []
    with pytest.raises(LiveProviderError, match="outside exact approval"):
        provider.read_values("example.com", "other", "A")
    with pytest.raises(LiveProviderError, match="exactly one"):
        provider.replace_values("example.com", "f093-abc", "A", ["1.1.1.1", "2.2.2.2"])


def test_config_rejects_broad_or_mismatched_authority(config):
    with pytest.raises(LiveProviderError, match="fqdn"):
        replace(config, fqdn="other.example.com").validate()
    with pytest.raises(LiveProviderError, match="root DNS"):
        replace(config, record_name="@").validate()
    with pytest.raises(LiveProviderError, match="source commit"):
        replace(config, source_commit="main").validate()
    with pytest.raises(LiveProviderError, match="wait"):
        replace(config, maximum_wait_attempts=1000).validate()


def test_duplicate_dns_records_fail_closed_without_overwrite(config):
    client, remote = Client(), Remote()
    client.domains.records = [
        {"id": 1, "type": "A", "name": "f093-abc", "data": "192.0.2.1"},
        {"id": 2, "type": "A", "name": "f093-abc", "data": "192.0.2.2"},
    ]
    provider = LiveDigitalOceanProvider(client, config, remote, sleep=lambda _delay: None)
    with pytest.raises(LiveProviderError, match="duplicate"):
        provider.replace_values("example.com", "f093-abc", "A", ["192.0.2.42"])
    assert not [call for call in client.domains.calls if call[0] != "list"]


def test_lost_create_response_reconciles_exact_owned_resource(config):
    client, remote = Client(), Remote()
    original = client.droplets.create

    def response_lost(payload):
        original(payload)
        raise TimeoutError("response lost after create")

    client.droplets.create = response_lost
    provider = LiveDigitalOceanProvider(client, config, remote, sleep=lambda _delay: None)
    row = provider.provision("base2-preview:lease-test:site:abcdef")
    assert row["id"] == 42
    assert len(client.droplets.rows) == 1
