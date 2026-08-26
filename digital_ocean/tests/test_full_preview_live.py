from datetime import UTC, datetime
from pathlib import Path

import pytest

from digital_ocean.scripts.python.full_preview_live import launch
from digital_ocean.scripts.python.preview_lease_v2 import FullPreviewLeaseStore


class Droplets:
    def __init__(self): self.row = None; self.deleted = []
    def list(self, tag_name=None): return {"droplets": [] if self.row is None else [self.row]}
    def create(self, payload):
        assert payload["ssh_keys"] == [77]
        self.row = {"id": 123, "name": payload["name"], "tags": payload["tags"], "status": "active", "size_slug": payload["size"], "created_at": "2026-08-26T00:00:00Z", "networks": {"v4": [{"type": "public", "ip_address": "8.8.8.8"}]}}
        return {"droplet": self.row}
    def get(self, provider_id): return {"droplet": self.row}
    def delete(self, provider_id): self.deleted.append(provider_id); self.row = None


class Domains:
    def __init__(self): self.rows = [{"id": 1, "type": "A", "name": "admin", "data": "9.9.9.9"}]; self.next = 10
    def list_records(self, domain): return {"domain_records": list(self.rows)}
    def create_record(self, domain, payload):
        row = {"id": self.next, **payload}; self.next += 1; self.rows.append(row)
        return {"domain_record": row}
    def delete_record(self, domain, record_id): self.rows = [row for row in self.rows if row["id"] != record_id]


class Client:
    def __init__(self): self.droplets = Droplets(); self.domains = Domains()


class Remote:
    def __init__(self): self.deployed = []
    def deploy(self, address, config): self.deployed.append((address, config.zone))
    def health(self, address, fqdn): return True


def files(tmp_path: Path):
    archive = tmp_path / "source.tar"; archive.write_bytes(b"archive")
    key = tmp_path / "id"; key.write_text("key"); key.chmod(0o600)
    return archive, key


def test_providerless_complete_launch_binds_six_records_and_private_lease(tmp_path):
    archive, key = files(tmp_path)
    client = Client(); remote = Remote()
    result = launch(
        client=client, remote=remote, source_archive=archive, ssh_key=key,
        source_commit="a" * 40, profile_digest="b" * 64, domain="woodkilldev.com",
        owner_cidr="8.8.4.4/32", run_id="base2-full-20260826-001",
        probe_username="owner", probe_password="safe-password", state_root=tmp_path / "state",
        ssh_key_id=77, clock=lambda: datetime(2026, 8, 26, tzinfo=UTC),
        probe=lambda *args, **kwargs: {"ok": True, "routeCount": 8},
    )
    assert result["status"] == "live-verified"
    assert result["dnsRecordCount"] == 6
    lease = FullPreviewLeaseStore(tmp_path / "state" / "leases").load(result["runId"])
    assert len(lease["dnsRecords"]) == 6
    assert [row["name"] for row in client.domains.rows] == [
        "woodkilldev.com", "admin", "swagger", "traefik", "pgadmin", "flower",
    ]


def test_probe_failure_restores_legacy_dns_and_deletes_compute(tmp_path):
    archive, key = files(tmp_path); client = Client()
    with pytest.raises(RuntimeError, match="probe"):
        launch(
            client=client, remote=Remote(), source_archive=archive, ssh_key=key,
            source_commit="a" * 40, profile_digest="b" * 64, domain="woodkilldev.com",
            owner_cidr="8.8.4.4/32", run_id="base2-full-20260826-002",
            probe_username="owner", probe_password="safe-password", state_root=tmp_path / "state",
            ssh_key_id=77, probe=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("probe failed")),
        )
    assert client.droplets.deleted == [123]
    assert [(row["name"], row["data"]) for row in client.domains.rows] == [("admin", "9.9.9.9")]


def test_hostile_preflight_performs_zero_provider_mutation(tmp_path):
    archive, key = files(tmp_path); client = Client()
    with pytest.raises(Exception, match="run ID"):
        launch(
            client=client, remote=Remote(), source_archive=archive, ssh_key=key,
            source_commit="a" * 40, profile_digest="b" * 64, domain="woodkilldev.com",
            owner_cidr="8.8.4.4/32", run_id="../unsafe", probe_username="owner",
            probe_password="safe-password", state_root=tmp_path / "state", ssh_key_id=77,
        )
    assert client.droplets.row is None and client.droplets.deleted == []
