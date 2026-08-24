from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from digital_ocean.scripts.python.deployment_evidence import EvidenceStore
from digital_ocean.scripts.python.dns_transaction import (
    DnsConflict,
    apply_dns_transaction,
    apply_dns_with_evidence,
    restore_dns_transaction,
)
from digital_ocean.scripts.python.preview_lease import LeaseStore

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def payload(mutations):
    return {
        "schemaVersion": 1,
        "leaseId": "lease-dns-001",
        "siteId": "base2-test",
        "sourceCommit": "a" * 40,
        "manifestDigest": "b" * 64,
        "owner": "owner:test",
        "state": "bootstrapping",
        "createdAt": NOW.isoformat().replace("+00:00", "Z"),
        "expiresAt": (NOW + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        "costPolicy": {"currency": "USD", "maximumMinorUnits": 100},
        "resources": [],
        "dnsMutations": mutations,
    }


def mutation(name="preview", previous=None, desired=None):
    return {
        "zone": "example.test",
        "name": name,
        "type": "A",
        "previousValues": previous or ["192.0.2.10"],
        "desiredValues": desired or ["192.0.2.20"],
        "state": "planned",
    }


class FakeDns:
    def __init__(self, values):
        self.values = dict(values)
        self.changes = []

    def read_values(self, zone, name, record_type):
        return list(self.values.get((zone, name, record_type), []))

    def replace_values(self, zone, name, record_type, values):
        self.changes.append((zone, name, record_type, list(values)))
        self.values[(zone, name, record_type)] = list(values)


def test_staged_apply_health_gate_and_exact_prior_receipt(tmp_path):
    item = mutation()
    store = LeaseStore(tmp_path)
    store.create(payload([item]))
    provider = FakeDns({("example.test", "preview", "A"): item["previousValues"]})
    result = apply_dns_transaction(
        store,
        provider,
        "lease-dns-001",
        health_check=lambda: True,
        required_sans={"preview.example.test"},
        certificate_sans={"preview.example.test"},
    )
    assert result["dnsMutations"][0]["state"] == "verified"
    assert provider.changes == [("example.test", "preview", "A", item["desiredValues"])]


def test_failed_health_rolls_back_exact_prior_values(tmp_path):
    item = mutation()
    store = LeaseStore(tmp_path)
    store.create(payload([item]))
    provider = FakeDns({("example.test", "preview", "A"): item["previousValues"]})
    with pytest.raises(DnsConflict, match="health"):
        apply_dns_transaction(
            store,
            provider,
            "lease-dns-001",
            health_check=lambda: False,
            required_sans={"preview.example.test"},
            certificate_sans={"preview.example.test"},
        )
    assert provider.read_values("example.test", "preview", "A") == item["previousValues"]
    assert store.load("lease-dns-001")["dnsMutations"][0]["state"] == "restored"


def test_stale_record_and_wrong_san_set_fail_before_mutation(tmp_path):
    item = mutation()
    store = LeaseStore(tmp_path)
    store.create(payload([item]))
    provider = FakeDns({("example.test", "preview", "A"): ["203.0.113.99"]})
    with pytest.raises(DnsConflict, match="stale"):
        apply_dns_transaction(
            store,
            provider,
            "lease-dns-001",
            health_check=lambda: True,
            required_sans={"preview.example.test"},
            certificate_sans={"preview.example.test"},
        )
    assert provider.changes == []
    provider.values[("example.test", "preview", "A")] = item["previousValues"]
    with pytest.raises(DnsConflict, match="SAN"):
        apply_dns_transaction(
            store,
            provider,
            "lease-dns-001",
            health_check=lambda: True,
            required_sans={"preview.example.test"},
            certificate_sans={"other.example.test"},
        )
    assert provider.changes == []
    with pytest.raises(DnsConflict, match="mutation names"):
        apply_dns_transaction(
            store,
            provider,
            "lease-dns-001",
            health_check=lambda: True,
            required_sans={"unrelated.example.test"},
            certificate_sans={"unrelated.example.test"},
        )


def test_interrupted_after_remote_apply_resumes_without_second_write(tmp_path):
    item = mutation()
    store = LeaseStore(tmp_path)
    store.create(payload([item]))
    provider = FakeDns({("example.test", "preview", "A"): item["desiredValues"]})
    result = apply_dns_transaction(
        store,
        provider,
        "lease-dns-001",
        health_check=lambda: True,
        required_sans={"preview.example.test"},
        certificate_sans={"preview.example.test"},
    )
    assert result["dnsMutations"][0]["state"] == "verified"
    assert provider.changes == []


def test_multi_record_failure_rolls_back_in_reverse_order(tmp_path):
    first, second = mutation("one"), mutation("two")
    store = LeaseStore(tmp_path)
    store.create(payload([first, second]))
    provider = FakeDns(
        {
            ("example.test", "one", "A"): first["previousValues"],
            ("example.test", "two", "A"): second["previousValues"],
        }
    )
    with pytest.raises(DnsConflict):
        apply_dns_transaction(
            store,
            provider,
            "lease-dns-001",
            health_check=lambda: False,
            required_sans={"one.example.test", "two.example.test"},
            certificate_sans={"one.example.test", "two.example.test"},
        )
    assert [change[1] for change in provider.changes] == ["one", "two", "two", "one"]


@pytest.mark.parametrize("initial_state", ["planned", "applied", "verified"])
def test_explicit_restore_accepts_only_exact_prior_or_desired_state(tmp_path, initial_state):
    item = mutation()
    item["state"] = initial_state
    store = LeaseStore(tmp_path)
    store.create(payload([item]))
    current = item["previousValues"] if initial_state == "planned" else item["desiredValues"]
    provider = FakeDns({("example.test", "preview", "A"): current})
    restored = restore_dns_transaction(store, provider, "lease-dns-001")
    assert restored["dnsMutations"][0]["state"] == "restored"
    assert provider.read_values("example.test", "preview", "A") == item["previousValues"]


def test_explicit_restore_refuses_third_party_dns_drift(tmp_path):
    item = mutation()
    item["state"] = "verified"
    store = LeaseStore(tmp_path)
    store.create(payload([item]))
    provider = FakeDns({("example.test", "preview", "A"): ["203.0.113.55"]})
    with pytest.raises(DnsConflict, match="restoration refused"):
        restore_dns_transaction(store, provider, "lease-dns-001")
    assert provider.changes == []
    assert store.load("lease-dns-001")["dnsMutations"][0]["state"] == "verified"


def test_dns_orchestrator_emits_terminal_evidence(tmp_path):
    item = mutation()
    store = LeaseStore(tmp_path / "leases")
    store.create(payload([item]))
    provider = FakeDns({("example.test", "preview", "A"): item["previousValues"]})
    evidence = {
        "schemaVersion": 1,
        "runId": "run-dns-001",
        "leaseId": "lease-dns-001",
        "sourceCommit": "a" * 40,
        "manifestDigest": "b" * 64,
        "action": "deploy",
        "status": "running",
        "startedAt": "2026-08-24T20:00:00Z",
        "finishedAt": None,
        "stages": [],
        "cost": {
            "currency": "USD",
            "ceilingMinorUnits": 100,
            "projectedMinorUnits": 5,
            "actualMinorUnits": 0,
            "withinBudget": True,
        },
        "artifacts": [],
        "failure": None,
    }
    times = iter(NOW + timedelta(seconds=value) for value in range(5))
    result, receipt = apply_dns_with_evidence(
        store,
        provider,
        "lease-dns-001",
        health_check=lambda: True,
        required_sans={"preview.example.test"},
        certificate_sans={"preview.example.test"},
        evidence_store=EvidenceStore(tmp_path / "evidence"),
        evidence=evidence,
        actual_minor_units=3,
        clock=lambda: next(times),
    )
    assert result["dnsMutations"][0]["state"] == "verified"
    assert receipt["status"] == "passed"
    assert receipt["stages"][0]["id"] == "dns"
