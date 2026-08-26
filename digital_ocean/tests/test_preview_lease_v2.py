from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from digital_ocean.scripts.python.preview_lease_v2 import (
    FullPreviewLeaseStore,
    LeaseV2Conflict,
    LeaseV2IntegrityError,
    LeaseV2ValidationError,
    TeardownNotDue,
    teardown_full_preview,
)


NOW = datetime(2026, 8, 26, 0, 0, tzinfo=UTC)


def payload(**overrides):
    value = {
        "schemaVersion": 2,
        "runId": "base2-full-20260826-001",
        "state": "live-verified",
        "armedAt": NOW.isoformat().replace("+00:00", "Z"),
        "expiresAt": (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "sourceCommit": "a" * 40,
        "sourceArchiveSha256": "b" * 64,
        "profileId": "base2-obsidian",
        "profileDigest": "c" * 64,
        "droplet": {
            "id": "123",
            "name": "base2-full-preview",
            "tags": ["base2", "base2-full-20260826-001"],
            "size": "s-2vcpu-2gb",
            "createdAt": NOW.isoformat().replace("+00:00", "Z"),
        },
        "dnsRecords": [
            {"id": "41", "domain": "woodkilldev.com", "type": "A", "name": "@", "value": "203.0.113.8", "state": "bound"},
            {"id": "42", "domain": "woodkilldev.com", "type": "A", "name": "admin", "value": "203.0.113.8", "state": "bound"},
        ],
        "ownerAdmissionDigest": "d" * 64,
        "certificateMode": "letsencrypt-staging-only",
        "budgetCeilingUsd": "0.25",
        "lastError": None,
        "mutationCounts": {"dropletsDeleted": 0, "dnsRecordsDeleted": 0},
    }
    value.update(overrides)
    return value


class Provider:
    def __init__(self):
        self.droplet = dict(payload()["droplet"])
        self.records = {row["id"]: dict(row) for row in payload()["dnsRecords"]}
        self.calls = []
        self.fail_dns = False

    def get_droplet(self, resource_id):
        return dict(self.droplet) if self.droplet and self.droplet["id"] == resource_id else None

    def delete_droplet(self, resource_id):
        self.calls.append(("delete-droplet", resource_id))
        self.droplet = None

    def list_owned_droplets(self, run_id):
        return [dict(self.droplet)] if self.droplet and run_id in self.droplet["tags"] else []

    def get_dns_record(self, domain, record_id):
        row = self.records.get(record_id)
        return dict(row) if row else None

    def delete_dns_record(self, domain, record_id):
        if self.fail_dns:
            raise RuntimeError("dns unavailable")
        self.calls.append(("delete-dns", record_id))
        self.records.pop(record_id, None)


def test_private_atomic_state_and_tamper_detection(tmp_path):
    store = FullPreviewLeaseStore(tmp_path)
    store.create(payload())
    assert store.load(payload()["runId"])["state"] == "live-verified"
    assert (tmp_path.stat().st_mode & 0o777) == 0o700
    path = tmp_path / f"{payload()['runId']}.json"
    assert (path.stat().st_mode & 0o777) == 0o600
    path.write_text(path.read_text().replace("live-verified", "destroyed"))
    with pytest.raises(LeaseV2IntegrityError):
        store.load(payload()["runId"])


def test_unknown_fields_and_wrong_certificate_mode_reject(tmp_path):
    with pytest.raises(LeaseV2ValidationError):
        FullPreviewLeaseStore(tmp_path).create(payload(extra=True))
    with pytest.raises(LeaseV2ValidationError, match="certificate"):
        FullPreviewLeaseStore(tmp_path / "two").create(payload(certificateMode="live"))


def test_unexpired_teardown_without_authority_mutates_nothing_and_is_not_success(tmp_path):
    store = FullPreviewLeaseStore(tmp_path)
    store.create(payload())
    provider = Provider()
    with pytest.raises(TeardownNotDue):
        teardown_full_preview(store, provider, payload()["runId"], now=NOW)
    assert provider.calls == []
    assert store.load(payload()["runId"])["state"] == "live-verified"


def test_approved_early_teardown_deletes_compute_before_exact_dns(tmp_path):
    store = FullPreviewLeaseStore(tmp_path)
    store.create(payload())
    provider = Provider()
    result = teardown_full_preview(store, provider, payload()["runId"], now=NOW, early_approved=True)
    assert result["state"] == "destroyed"
    assert provider.calls == [("delete-droplet", "123"), ("delete-dns", "41"), ("delete-dns", "42")]
    assert result["mutationCounts"] == {"dropletsDeleted": 1, "dnsRecordsDeleted": 2}


def test_expired_teardown_needs_no_early_authority_and_replay_is_noop(tmp_path):
    store = FullPreviewLeaseStore(tmp_path)
    store.create(payload())
    provider = Provider()
    result = teardown_full_preview(store, provider, payload()["runId"], now=NOW + timedelta(hours=2))
    before = list(provider.calls)
    replay = teardown_full_preview(store, provider, payload()["runId"], now=NOW + timedelta(hours=2))
    assert result == replay
    assert provider.calls == before


def test_dns_failure_persists_recoverable_state_after_compute_absent(tmp_path):
    store = FullPreviewLeaseStore(tmp_path)
    store.create(payload())
    provider = Provider()
    provider.fail_dns = True
    with pytest.raises(RuntimeError, match="dns unavailable"):
        teardown_full_preview(store, provider, payload()["runId"], now=NOW, early_approved=True)
    assert provider.droplet is None
    assert store.load(payload()["runId"])["state"] == "dns-cleanup-pending"
    provider.fail_dns = False
    result = teardown_full_preview(store, provider, payload()["runId"], now=NOW, early_approved=True)
    assert result["state"] == "destroyed"


def test_identity_drift_fails_before_any_delete(tmp_path):
    store = FullPreviewLeaseStore(tmp_path)
    store.create(payload())
    provider = Provider()
    provider.droplet["size"] = "s-8vcpu-16gb"
    with pytest.raises(LeaseV2Conflict, match="identity"):
        teardown_full_preview(store, provider, payload()["runId"], now=NOW, early_approved=True)
    assert provider.calls == []


def test_dns_identity_drift_fails_closed_after_compute_and_remains_pending(tmp_path):
    store = FullPreviewLeaseStore(tmp_path)
    store.create(payload())
    provider = Provider()
    provider.records["41"]["value"] = "203.0.113.99"
    with pytest.raises(LeaseV2Conflict, match="DNS identity"):
        teardown_full_preview(store, provider, payload()["runId"], now=NOW, early_approved=True)
    assert provider.droplet is None
    assert store.load(payload()["runId"])["state"] == "dns-cleanup-pending"
