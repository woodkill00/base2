from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from digital_ocean.scripts.python.deployment_evidence import (
    EvidenceIntegrityError,
    EvidenceStore,
)
from digital_ocean.scripts.python.dns_transaction import DnsConflict
from digital_ocean.scripts.python.preview_lease import LeaseStore, ownership_tag
from digital_ocean.scripts.python.preview_orchestrator import (
    PreviewOrchestrationError,
    PreviewOrchestrator,
)
from digital_ocean.scripts.python.provider_admission import (
    AdmissionDenied,
    AdmissionPolicy,
    AdmissionSnapshot,
    ProviderAdmissionController,
)

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def lease_payload(*, with_dns=True):
    mutations = []
    if with_dns:
        mutations = [
            {
                "zone": "example.test",
                "name": "preview",
                "type": "A",
                "previousValues": ["192.0.2.10"],
                "desiredValues": ["192.0.2.20"],
                "state": "planned",
            }
        ]
    return {
        "schemaVersion": 1,
        "leaseId": "lease-flow-001",
        "siteId": "base2-test",
        "sourceCommit": "a" * 40,
        "manifestDigest": "b" * 64,
        "owner": "owner:test",
        "state": "planned",
        "createdAt": "2026-08-24T20:00:00Z",
        "expiresAt": "2026-08-24T22:00:00Z",
        "costPolicy": {"currency": "USD", "maximumMinorUnits": 100},
        "resources": [],
        "dnsMutations": mutations,
    }


def evidence(run_id="run-flow-001", action="deploy"):
    return {
        "schemaVersion": 1,
        "runId": run_id,
        "leaseId": "lease-flow-001",
        "sourceCommit": "a" * 40,
        "manifestDigest": "b" * 64,
        "action": action,
        "status": "running",
        "startedAt": "2026-08-24T20:00:00Z",
        "finishedAt": None,
        "stages": [],
        "cost": {
            "currency": "USD",
            "ceilingMinorUnits": 100,
            "projectedMinorUnits": 10,
            "actualMinorUnits": 0,
            "withinBudget": True,
        },
        "artifacts": [],
        "failure": None,
    }


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.resources = {}
        self.dns = {("example.test", "preview", "A"): ["192.0.2.10"]}
        self.healthy = True
        self.fail_provision = False

    def provision(self, tag):
        self.calls.append(("provision", tag))
        if self.fail_provision:
            raise RuntimeError("provider failed")
        item = {"id": "123", "tags": [tag]}
        self.resources[("digitalocean", "droplet", "123")] = item
        return item

    def bootstrap(self, provider_id):
        self.calls.append(("bootstrap", provider_id))

    def health(self, provider_id):
        self.calls.append(("health", provider_id))
        return self.healthy

    def read_values(self, zone, name, record_type):
        return list(self.dns.get((zone, name, record_type), []))

    def replace_values(self, zone, name, record_type, values):
        self.calls.append(("dns", name, list(values)))
        self.dns[(zone, name, record_type)] = list(values)

    def get_resource(self, provider, kind, provider_id):
        return self.resources.get((provider, kind, provider_id))

    def delete_resource(self, provider, kind, provider_id):
        self.calls.append(("delete", provider_id))
        self.resources.pop((provider, kind, provider_id), None)

    def list_owned_resources(self, tag):
        return [item for item in self.resources.values() if tag in item["tags"]]


def orchestrator(tmp_path, provider, *, snapshot_overrides=None):
    times = iter(NOW + timedelta(seconds=value) for value in range(40))
    snapshot_values = {
        "active_resources": 0,
        "provider_quota": 5,
        "projected_minor_units": 10,
        "budget_ceiling_minor_units": 100,
        "disk_free_bytes": 2_000,
        "memory_available_bytes": 2_000,
        "oom_kills": 0,
    }
    snapshot_values.update(snapshot_overrides or {})
    admission = ProviderAdmissionController(
        tmp_path / "admission",
        AdmissionPolicy(
            maximum_active_resources=2,
            minimum_disk_free_bytes=1_000,
            minimum_memory_available_bytes=1_000,
        ),
        clock=lambda: NOW,
        sleep=lambda _delay: None,
    )
    return PreviewOrchestrator(
        LeaseStore(tmp_path / "leases"),
        EvidenceStore(tmp_path / "evidence"),
        provider,
        admission,
        lambda: AdmissionSnapshot(**snapshot_values),
        clock=lambda: next(times),
        sleep=lambda _delay: None,
    )


def test_first_deploy_dns_health_and_exact_replay(tmp_path):
    provider = FakeProvider()
    flow = orchestrator(tmp_path, provider)
    lease, receipt = flow.deploy(
        lease_payload(), evidence(), certificate_sans={"preview.example.test"}, actual_minor_units=7
    )
    assert lease["state"] == "healthy" and receipt["status"] == "passed"
    assert [stage["id"] for stage in receipt["stages"]] == [
        "admission",
        "provision",
        "bootstrap",
        "dns",
        "health",
    ]
    assert lease["resources"][0]["ownershipTag"] == ownership_tag(
        "lease-flow-001", "base2-test", "b" * 64
    )
    before = list(provider.calls)
    replay_lease, replay_receipt = flow.deploy(
        lease_payload(), evidence(), certificate_sans={"preview.example.test"}
    )
    assert replay_lease == lease and replay_receipt == receipt and provider.calls == before


def test_resume_bootstrapping_does_not_provision_again(tmp_path):
    provider = FakeProvider()
    flow = orchestrator(tmp_path, provider)
    lease = flow.leases.create(lease_payload(with_dns=False))
    lease = flow.leases.transition(lease["leaseId"], "provisioning")
    tag = ownership_tag(lease["leaseId"], lease["siteId"], lease["manifestDigest"])
    provider.resources[("digitalocean", "droplet", "123")] = {"id": "123", "tags": [tag]}
    flow.leases.add_resource(
        lease["leaseId"],
        {"provider": "digitalocean", "kind": "droplet", "providerId": "123", "ownershipTag": tag},
    )
    flow.leases.transition(lease["leaseId"], "bootstrapping")
    result, _ = flow.deploy(lease_payload(with_dns=False), evidence(), certificate_sans=set())
    assert result["state"] == "healthy"
    assert not any(call[0] == "provision" for call in provider.calls)


def test_provision_failure_is_terminal_and_rolls_back(tmp_path):
    provider = FakeProvider()
    provider.fail_provision = True
    flow = orchestrator(tmp_path, provider)
    with pytest.raises(RuntimeError, match="provider failed"):
        flow.deploy(lease_payload(), evidence(), certificate_sans={"preview.example.test"})
    assert flow.leases.load("lease-flow-001")["state"] == "destroyed"
    receipt = flow.evidence.load("run-flow-001")
    assert receipt["status"] == "failed" and receipt["failure"]["stage"] == "provision"


def test_resource_pressure_fails_admission_before_provider_mutation(tmp_path):
    provider = FakeProvider()
    flow = orchestrator(tmp_path, provider, snapshot_overrides={"disk_free_bytes": 1})
    with pytest.raises(AdmissionDenied, match="disk_pressure"):
        flow.deploy(lease_payload(), evidence(), certificate_sans={"preview.example.test"})
    assert provider.calls == []
    receipt = flow.evidence.load("run-flow-001")
    assert receipt["failure"] == {
        "stage": "admission",
        "code": "admission_failed",
        "retryable": False,
    }


def test_health_failure_deletes_exact_owned_resource(tmp_path):
    provider = FakeProvider()
    provider.healthy = False
    flow = orchestrator(tmp_path, provider)
    with pytest.raises(PreviewOrchestrationError, match="health"):
        flow.deploy(lease_payload(with_dns=False), evidence(), certificate_sans=set())
    assert ("delete", "123") in provider.calls
    assert flow.leases.load("lease-flow-001")["state"] == "destroyed"


def test_dns_health_failure_restores_prior_value_before_exact_delete(tmp_path):
    provider = FakeProvider()
    provider.healthy = False
    flow = orchestrator(tmp_path, provider)
    with pytest.raises(DnsConflict, match="health gate failed"):
        flow.deploy(
            lease_payload(),
            evidence(),
            certificate_sans={"preview.example.test"},
        )
    assert provider.dns[("example.test", "preview", "A")] == ["192.0.2.10"]
    assert provider.calls.index(("dns", "preview", ["192.0.2.10"])) < provider.calls.index(
        ("delete", "123")
    )
    assert flow.leases.load("lease-flow-001")["state"] == "destroyed"


def test_wrong_provider_ownership_fails_before_lease_admission(tmp_path):
    class WrongOwner(FakeProvider):
        def provision(self, tag):
            self.calls.append(("provision", tag))
            return {"id": "123", "tags": ["other-owner"]}

    provider = WrongOwner()
    flow = orchestrator(tmp_path, provider)
    with pytest.raises(PreviewOrchestrationError, match="ownership"):
        flow.deploy(lease_payload(with_dns=False), evidence(), certificate_sans=set())
    assert flow.leases.load("lease-flow-001")["resources"] == []
    assert not any(call[0] == "delete" for call in provider.calls)


def test_tampered_terminal_evidence_fails_closed_without_provider_calls(tmp_path):
    provider = FakeProvider()
    flow = orchestrator(tmp_path, provider)
    flow.deploy(lease_payload(with_dns=False), evidence(), certificate_sans=set())
    provider.calls.clear()
    path = tmp_path / "evidence" / "run-flow-001.json"
    path.write_text(path.read_text().replace('"status":"passed"', '"status":"failed"'))
    with pytest.raises(EvidenceIntegrityError):
        flow.deploy(lease_payload(with_dns=False), evidence(), certificate_sans=set())
    assert provider.calls == []


def test_update_and_explicit_rollback_paths(tmp_path):
    provider = FakeProvider()
    flow = orchestrator(tmp_path, provider)
    flow.deploy(lease_payload(with_dns=False), evidence(), certificate_sans=set())
    provider.calls.clear()
    lease, update_receipt = flow.update("lease-flow-001", evidence("run-update-001", "update"))
    assert lease["state"] == "healthy" and update_receipt["status"] == "passed"
    assert not any(call[0] == "provision" for call in provider.calls)
    rolled, rollback_receipt = flow.rollback(
        "lease-flow-001", evidence("run-rollback-001", "rollback")
    )
    assert rolled["state"] == "destroyed" and rollback_receipt["status"] == "passed"
