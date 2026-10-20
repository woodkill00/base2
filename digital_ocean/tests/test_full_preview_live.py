from datetime import UTC, datetime
from pathlib import Path
import json

import pytest

from digital_ocean.scripts.python.full_preview_live import launch
from digital_ocean.scripts.python.full_preview_remote import FullPreviewRemoteError, failure_stage, safe_diagnostic, failure_warmup_cause
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
        row = {"id": self.next, **payload}
        if row["name"] == f"{domain}.": row["name"] = "@"
        self.next += 1; self.rows.append(row)
        return {"domain_record": row}
    def delete_record(self, domain, record_id): self.rows = [row for row in self.rows if row["id"] != record_id]


class Client:
    def __init__(self): self.droplets = Droplets(); self.domains = Domains()


class Remote:
    def __init__(self): self.deployed = []
    def deploy(self, address, config): self.deployed.append((address, config.zone))
    def health(self, address, fqdn): return True


@pytest.mark.parametrize("cause", ["oom", "exited", "unhealthy", "deadline"])
def test_typed_warmup_cause_is_bounded_and_stage_bound(cause):
    marker = f"full-preview-warmup-cause:{cause}"
    assert failure_warmup_cause("", marker) == cause
    assert failure_warmup_cause(marker, marker) == "unknown"
    assert failure_warmup_cause(marker, "full-preview-warmup-cause:password=secret") == "unknown"
    assert FullPreviewRemoteError("", stage="clamav-warmup", warmup_cause=cause).warmup_cause == cause
    assert FullPreviewRemoteError("", stage="compose-build", warmup_cause=cause).warmup_cause == "unknown"


@pytest.mark.parametrize("cause", ["password=secret", "", None, {}, True])
def test_mutated_warmup_metadata_cannot_persist_arbitrary_values(tmp_path, cause):
    from digital_ocean.scripts.python.full_preview_live import _record_remote_failure
    error = FullPreviewRemoteError("", stage="clamav-warmup")
    error.warmup_cause = cause
    _record_remote_failure(tmp_path, "base2-full-20260826-099", "a" * 40, error)
    record = (tmp_path / "evidence/base2-full-20260826-099.failure.json").read_text()
    assert json.loads(record)["warmupCause"] == "unknown"
    assert "password" not in record

def files(tmp_path: Path):
    archive = tmp_path / "source.tar"; archive.write_bytes(b"archive")
    key = tmp_path / "id"; key.write_text("key"); key.chmod(0o600)
    return archive, key


@pytest.mark.parametrize("storage_failure", [False, True])
def test_remote_failure_metadata_survives_cleanup_without_secrets(tmp_path, monkeypatch, capsys, storage_failure):
    archive, key = files(tmp_path); client = Client()
    class FailedRemote(Remote):
        def deploy(self, address, config):
            raise FullPreviewRemoteError("password=never-persist", stage="clamav-warmup",
                                         reason="nonzero-exit", exit_code=4, warmup_cause="oom")
    if storage_failure:
        def fail(*args):
            raise OSError("secret-storage-error")
        monkeypatch.setattr("digital_ocean.scripts.python.full_preview_live._record_remote_failure", fail)
    with pytest.raises(FullPreviewRemoteError, match="never-persist"):
        launch(client=client, remote=FailedRemote(), source_archive=archive, ssh_key=key,
               source_commit="a" * 40, profile_digest="b" * 64, domain="woodkilldev.com",
               owner_cidr="8.8.4.4/32", run_id="base2-full-20260826-099",
               probe_username="owner", probe_password="safe-password", state_root=tmp_path / "state",
               ssh_key_id=77)
    assert client.droplets.deleted == [123]
    captured = capsys.readouterr()
    assert "secret-storage-error" not in captured.err
    if storage_failure:
        assert "failure-evidence:unavailable" in captured.err
    else:
        evidence = tmp_path / "state/evidence/base2-full-20260826-099.failure.json"
        record = json.loads(evidence.read_text())
        assert record["stage"] == "clamav-warmup" and record["exitCode"] == 4
        assert record["warmupCause"] == "oom"
        assert record["sourceCommit"] == "a" * 40
        assert "never-persist" not in evidence.read_text()
        assert evidence.stat().st_mode & 0o777 == 0o600


def test_failure_evidence_refuses_symlinks_and_overwrite(tmp_path):
    from digital_ocean.scripts.python.full_preview_live import _record_remote_failure
    error = FullPreviewRemoteError("secret", stage="secret", reason="secret", exit_code=True)
    _record_remote_failure(tmp_path, "base2-full-20260826-099", "a" * 40, error)
    path = tmp_path / "evidence/base2-full-20260826-099.failure.json"
    original = path.read_bytes()
    assert json.loads(original)["stage"] == "unknown"
    assert json.loads(original)["exitCode"] is None
    with pytest.raises(FileExistsError):
        _record_remote_failure(tmp_path, "base2-full-20260826-099", "a" * 40, error)
    assert path.read_bytes() == original
    root = tmp_path / "other"; root.mkdir()
    (root / "evidence").symlink_to(tmp_path / "evidence", target_is_directory=True)
    with pytest.raises(OSError):
        _record_remote_failure(root, "base2-full-20260826-098", "a" * 40, error)


@pytest.mark.parametrize("marker", ["full-preview-stage:password=secret",
    "full-preview-stage:compose-build secret", "full-preview-stage-failed:unknown exit=4"])
def test_untrusted_stage_markers_are_not_retained(marker):
    assert failure_stage("", marker) == "unknown"
    assert "secret" not in safe_diagnostic("", marker)
    assert failure_stage("full-preview-stage:compose-build", marker) == "compose-build"


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
        "@", "admin", "swagger", "traefik", "pgadmin", "flower",
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
