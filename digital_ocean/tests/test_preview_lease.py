from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from digital_ocean.scripts.python.preview_lease import (
    LeaseConflict,
    LeaseIntegrityError,
    LeaseStore,
    LeaseValidationError,
    ownership_tag,
)

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def lease_payload(**overrides):
    payload = {
        "schemaVersion": 1,
        "leaseId": "lease-test-001",
        "siteId": "base2-test",
        "sourceCommit": "a" * 40,
        "manifestDigest": "b" * 64,
        "owner": "owner:test",
        "state": "planned",
        "createdAt": NOW.isoformat().replace("+00:00", "Z"),
        "expiresAt": (NOW + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        "costPolicy": {"currency": "USD", "maximumMinorUnits": 100},
        "resources": [],
        "dnsMutations": [],
    }
    payload.update(overrides)
    return payload


def test_create_validates_contract_and_round_trips(tmp_path):
    store = LeaseStore(tmp_path)
    created = store.create(lease_payload())
    assert created == lease_payload()
    assert store.load("lease-test-001") == created
    assert (tmp_path.stat().st_mode & 0o777) == 0o700
    assert ((tmp_path / "lease-test-001.json").stat().st_mode & 0o777) == 0o600


def test_exact_create_replay_is_idempotent(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease_payload())
    path = tmp_path / "lease-test-001.json"
    before = (path.stat().st_ino, path.stat().st_mtime_ns, path.read_bytes())
    assert store.create(lease_payload()) == lease_payload()
    after = (path.stat().st_ino, path.stat().st_mtime_ns, path.read_bytes())
    assert after == before


def test_changed_create_replay_fails_closed(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease_payload())
    with pytest.raises(LeaseConflict, match="different lease"):
        store.create(lease_payload(owner="owner:other"))


def test_unknown_fields_and_bad_schema_values_are_rejected(tmp_path):
    store = LeaseStore(tmp_path)
    with pytest.raises(LeaseValidationError, match="unknown field"):
        store.create(lease_payload(unreviewed=True))
    with pytest.raises(LeaseValidationError, match="sourceCommit"):
        store.create(lease_payload(sourceCommit="main"))


def test_tampering_and_truncated_state_are_detected(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease_payload())
    path = tmp_path / "lease-test-001.json"
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["lease"]["owner"] = "attacker"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(LeaseIntegrityError, match="digest"):
        store.load("lease-test-001")
    path.write_text('{"lease":', encoding="utf-8")
    with pytest.raises(LeaseIntegrityError, match="valid JSON"):
        store.load("lease-test-001")


def test_atomic_write_interruption_preserves_previous_state(tmp_path, monkeypatch):
    store = LeaseStore(tmp_path)
    original = store.create(lease_payload())

    def interrupted(_source, _target):
        raise OSError("injected interruption")

    monkeypatch.setattr(os, "replace", interrupted)
    with pytest.raises(OSError, match="injected interruption"):
        store.transition("lease-test-001", "provisioning")
    assert store.load("lease-test-001") == original
    assert not list(tmp_path.glob("*.tmp"))


def test_state_transitions_are_bounded_and_replay_safe(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease_payload())
    current = store.transition("lease-test-001", "provisioning")
    assert current["state"] == "provisioning"
    assert store.transition("lease-test-001", "provisioning") == current
    with pytest.raises(LeaseConflict, match="transition"):
        store.transition("lease-test-001", "destroyed")


def test_expiry_reconciliation_and_bounded_renewal(tmp_path):
    store = LeaseStore(tmp_path, maximum_renewal=timedelta(hours=6))
    store.create(lease_payload())
    renewed = store.renew("lease-test-001", timedelta(hours=3), now=NOW)
    assert renewed["expiresAt"] == "2026-08-25T01:00:00Z"
    with pytest.raises(LeaseValidationError, match="renewal limit"):
        store.renew("lease-test-001", timedelta(hours=7), now=NOW)
    assert store.reconcile_expired(now=NOW + timedelta(hours=6)) == ["lease-test-001"]
    assert store.load("lease-test-001")["state"] == "teardown_due"


def test_terminal_lease_cannot_be_renewed(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease_payload(state="destroyed"))
    with pytest.raises(LeaseConflict, match="terminal"):
        store.renew("lease-test-001", timedelta(hours=1), now=NOW)


def test_resources_require_exact_deterministic_ownership_tag(tmp_path):
    expected = ownership_tag("lease-test-001", "base2-test", "b" * 64)
    resource = {
        "provider": "digitalocean",
        "kind": "droplet",
        "providerId": "12345",
        "ownershipTag": expected,
    }
    LeaseStore(tmp_path).create(lease_payload(resources=[resource]))

    wrong = {**resource, "ownershipTag": "base2-preview:someone-else"}
    with pytest.raises(LeaseValidationError, match="ownershipTag"):
        LeaseStore(tmp_path / "wrong").create(lease_payload(resources=[wrong]))


@pytest.mark.parametrize("lease_id", ["../escape", "short", "bad id", "a" * 129])
def test_hostile_lease_ids_are_rejected(tmp_path, lease_id):
    with pytest.raises(LeaseValidationError, match="leaseId"):
        LeaseStore(tmp_path).create(lease_payload(leaseId=lease_id))


def test_contract_schema_remains_bound_to_runtime_fields():
    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (
            root / "specs/093-base2-foundation-hardening/contracts/preview-lease.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(lease_payload())


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda item: item.update(schemaVersion=2), "schemaVersion"),
        (lambda item: item.update(siteId="Bad Site"), "siteId"),
        (lambda item: item.update(manifestDigest="short"), "manifestDigest"),
        (lambda item: item.update(owner=""), "owner"),
        (lambda item: item.update(state="unknown"), "state"),
        (lambda item: item.update(expiresAt=item["createdAt"]), "expiresAt"),
        (
            lambda item: item.update(costPolicy={"currency": "usd", "maximumMinorUnits": 1}),
            "currency",
        ),
        (
            lambda item: item.update(costPolicy={"currency": "USD", "maximumMinorUnits": -1}),
            "maximumMinorUnits",
        ),
        (lambda item: item.update(resources="not-a-list"), "resources"),
        (lambda item: item.update(dnsMutations="not-a-list"), "dnsMutations"),
    ],
)
def test_additional_contract_failures_are_typed(tmp_path, change, match):
    item = lease_payload()
    change(item)
    with pytest.raises(LeaseValidationError, match=match):
        LeaseStore(tmp_path).create(item)
