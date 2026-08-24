from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from digital_ocean.scripts.python.orchestrate_teardown import (
    TeardownConflict,
    teardown_lease,
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
