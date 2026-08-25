from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest

from digital_ocean.scripts.python.deployment_evidence import EvidenceStore
from digital_ocean.scripts.python.orchestrate_teardown import (
    DigitalOceanProvider,
    TeardownConflict,
    main,
    teardown_lease,
    teardown_lease_with_evidence,
)
from digital_ocean.scripts.python.preview_lease import (
    LeaseIntegrityError,
    LeaseStore,
    ownership_tag,
)

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def payload(provider_id="123"):
    digest = "b" * 64
    return {
        "schemaVersion": 1,
        "leaseId": "lease-delete-001",
        "siteId": "base2-test",
        "sourceCommit": "a" * 40,
        "manifestDigest": digest,
        "owner": "owner:test",
        "state": "healthy",
        "createdAt": NOW.isoformat().replace("+00:00", "Z"),
        "expiresAt": (NOW + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        "costPolicy": {"currency": "USD", "maximumMinorUnits": 100},
        "resources": [
            {
                "provider": "digitalocean",
                "kind": "droplet",
                "providerId": provider_id,
                "ownershipTag": ownership_tag("lease-delete-001", "base2-test", digest),
            }
        ],
        "dnsMutations": [],
    }


class FakeProvider:
    def __init__(self, resources, *, residual=None):
        self.resources = dict(resources)
        self.residual = residual
        self.deleted = []

    def get_resource(self, provider, kind, provider_id):
        return self.resources.get((provider, kind, provider_id))

    def delete_resource(self, provider, kind, provider_id):
        self.deleted.append((provider, kind, provider_id))
        self.resources.pop((provider, kind, provider_id), None)

    def list_owned_resources(self, ownership_tag):
        if self.residual is not None:
            return self.residual
        return [item for item in self.resources.values() if ownership_tag in item["tags"]]


def test_exact_owned_resource_is_deleted_and_zero_verified(tmp_path):
    store = LeaseStore(tmp_path)
    lease = store.create(payload())
    resource = lease["resources"][0]
    provider = FakeProvider(
        {("digitalocean", "droplet", "123"): {"id": "123", "tags": [resource["ownershipTag"]]}}
    )
    result = teardown_lease(store, provider, lease["leaseId"])
    assert result["state"] == "destroyed"
    assert provider.deleted == [("digitalocean", "droplet", "123")]
    assert result["deletedProviderIds"] == ["123"]


@pytest.mark.parametrize(
    "remote",
    [
        {"id": "replacement", "tags": []},
        {"id": "123", "tags": ["base2-preview:different"]},
    ],
)
def test_wrong_id_or_tag_fails_before_delete(tmp_path, remote):
    store = LeaseStore(tmp_path)
    store.create(payload())
    provider = FakeProvider({("digitalocean", "droplet", "123"): remote})
    with pytest.raises(TeardownConflict, match="ownership"):
        teardown_lease(store, provider, "lease-delete-001")
    assert provider.deleted == []


def test_missing_resource_is_idempotent_and_name_replacement_is_ignored(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(payload())
    provider = FakeProvider(
        {("digitalocean", "droplet", "999"): {"id": "999", "name": "same-name", "tags": []}}
    )
    first = teardown_lease(store, provider, "lease-delete-001")
    second = teardown_lease(store, provider, "lease-delete-001")
    assert first["state"] == second["state"] == "destroyed"
    assert provider.deleted == []


def test_missing_receipt_and_tampered_digest_fail_closed(tmp_path):
    store = LeaseStore(tmp_path)
    with pytest.raises(LeaseIntegrityError):
        teardown_lease(store, FakeProvider({}), "lease-delete-001")
    store.create(payload())
    path = tmp_path / "lease-delete-001.json"
    path.write_text(path.read_text().replace('"owner":"owner:test"', '"owner":"changed"'))
    with pytest.raises(LeaseIntegrityError):
        teardown_lease(store, FakeProvider({}), "lease-delete-001")


def test_residual_owned_resource_blocks_destroyed_receipt(tmp_path):
    store = LeaseStore(tmp_path)
    lease = store.create(payload())
    resource = lease["resources"][0]
    provider = FakeProvider(
        {("digitalocean", "droplet", "123"): {"id": "123", "tags": [resource["ownershipTag"]]}},
        residual=[{"id": "456"}],
    )
    with pytest.raises(TeardownConflict, match="zero-resource"):
        teardown_lease(store, provider, "lease-delete-001", sleep=lambda _delay: None)
    assert store.load("lease-delete-001")["state"] == "destroying"


def test_provider_rate_limit_is_bounded_and_reported(tmp_path):
    class RateLimited(RuntimeError):
        status_code = 429

    class Limited(FakeProvider):
        calls = 0

        def delete_resource(self, provider, kind, provider_id):
            self.calls += 1
            raise RateLimited("rate limited")

    store = LeaseStore(tmp_path)
    lease = store.create(payload())
    resource = lease["resources"][0]
    provider = Limited(
        {("digitalocean", "droplet", "123"): {"id": "123", "tags": [resource["ownershipTag"]]}}
    )
    with pytest.raises(RateLimited, match="rate limited"):
        teardown_lease(store, provider, "lease-delete-001", sleep=lambda _delay: None)
    assert provider.calls == 3
    assert store.load("lease-delete-001")["state"] == "destroying"


def test_dns_receipt_and_invalid_attempt_limits_fail_before_provider(tmp_path):
    store = LeaseStore(tmp_path)
    item = payload()
    item["dnsMutations"] = [
        {
            "zone": "example.test",
            "name": "preview",
            "type": "A",
            "previousValues": [],
            "desiredValues": ["192.0.2.1"],
            "state": "planned",
        }
    ]
    store.create(item)
    with pytest.raises(TeardownConflict, match="DNS mutations"):
        teardown_lease(store, FakeProvider({}), "lease-delete-001")
    with pytest.raises(ValueError, match="attempt limits"):
        teardown_lease(store, FakeProvider({}), "lease-delete-001", provider_attempts=0)


def test_digitalocean_adapter_is_exact_and_allowlisted():
    class NotFound(RuntimeError):
        status_code = 404

    droplets = mock.Mock()
    droplets.get.return_value = {"droplet": {"id": 123, "tags": ["owned"]}}
    droplets.list.return_value = {"droplets": [{"id": 123}]}
    client = mock.Mock(droplets=droplets)
    adapter = DigitalOceanProvider(client)
    assert adapter.get_resource("digitalocean", "droplet", "123")["id"] == 123
    adapter.delete_resource("digitalocean", "droplet", "123")
    assert adapter.list_owned_resources("owned") == [{"id": 123}]
    droplets.get.side_effect = NotFound("missing")
    assert adapter.get_resource("digitalocean", "droplet", "123") is None
    droplets.get.side_effect = RuntimeError("provider down")
    with pytest.raises(RuntimeError, match="provider down"):
        adapter.get_resource("digitalocean", "droplet", "123")
    with pytest.raises(TeardownConflict, match="allowlisted"):
        adapter.delete_resource("other", "droplet", "123")


def test_cli_refuses_dns_and_missing_token(monkeypatch, tmp_path, capsys):
    args = ["--lease-id", "lease-delete-001", "--lease-root", str(tmp_path)]
    assert main([*args, "--clean-dns"]) == 2
    monkeypatch.setattr(
        "digital_ocean.scripts.python.orchestrate_teardown.load_deploy_config", lambda _path: {}
    )
    monkeypatch.delenv("DO_API_TOKEN", raising=False)
    assert main(args) == 2
    assert "DO_API_TOKEN" in capsys.readouterr().err


def test_cli_reports_optional_pydo_without_blocking_library_import(
    monkeypatch, tmp_path, capsys
):
    args = ["--lease-id", "lease-delete-001", "--lease-root", str(tmp_path)]
    monkeypatch.setattr(
        "digital_ocean.scripts.python.orchestrate_teardown.load_deploy_config",
        lambda _path: {"DO_API_TOKEN": "secret"},
    )
    monkeypatch.setattr("digital_ocean.scripts.python.orchestrate_teardown.Client", None)
    assert main(args) == 2
    assert "standalone teardown CLI" in capsys.readouterr().err


def test_live_canary_imports_with_only_the_standard_library():
    repo_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import digital_ocean.scripts.python.live_canary; print('stdlib-import-ok')",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "stdlib-import-ok"


def test_cli_success_uses_lease_bound_path(monkeypatch, tmp_path, capsys):
    args = ["--lease-id", "lease-delete-001", "--lease-root", str(tmp_path)]
    monkeypatch.setattr(
        "digital_ocean.scripts.python.orchestrate_teardown.load_deploy_config",
        lambda _path: {"DO_API_TOKEN": "secret"},
    )
    monkeypatch.setattr("digital_ocean.scripts.python.orchestrate_teardown.Client", mock.Mock())
    monkeypatch.setattr(
        "digital_ocean.scripts.python.orchestrate_teardown.teardown_lease",
        lambda _store, _provider, lease_id: {
            "leaseId": lease_id,
            "state": "destroyed",
            "deletedProviderIds": [],
        },
    )
    assert main(args) == 0
    assert '"state": "destroyed"' in capsys.readouterr().out


def test_teardown_orchestrator_emits_terminal_evidence(tmp_path):
    store = LeaseStore(tmp_path / "leases")
    store.create(payload())
    evidence = {
        "schemaVersion": 1,
        "runId": "run-delete-001",
        "leaseId": "lease-delete-001",
        "sourceCommit": "a" * 40,
        "manifestDigest": "b" * 64,
        "action": "teardown",
        "status": "running",
        "startedAt": "2026-08-24T20:00:00Z",
        "finishedAt": None,
        "stages": [],
        "cost": {
            "currency": "USD",
            "ceilingMinorUnits": 100,
            "projectedMinorUnits": 0,
            "actualMinorUnits": 0,
            "withinBudget": True,
        },
        "artifacts": [],
        "failure": None,
    }
    times = iter(NOW + timedelta(seconds=value) for value in range(5))
    result, receipt = teardown_lease_with_evidence(
        store,
        FakeProvider({}),
        "lease-delete-001",
        evidence_store=EvidenceStore(tmp_path / "evidence"),
        evidence=evidence,
        actual_minor_units=0,
        clock=lambda: next(times),
        sleep=lambda _delay: None,
    )
    assert result["state"] == "destroyed"
    assert receipt["status"] == "passed"
    assert receipt["stages"][0]["id"] == "teardown"
