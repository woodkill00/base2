"""Provider-free crash boundaries: BaseException models process interruption."""

from datetime import UTC, datetime, timedelta

import pytest

from digital_ocean.scripts.python.full_preview_live import launch
from digital_ocean.scripts.python.preview_lease_v2 import (
    FullPreviewLeaseStore,
    LeaseV2Conflict,
    teardown_full_preview,
)
from digital_ocean.tests.test_full_preview_live import Client, Remote, files

RUN = "base2-full-20261014-001"
NOW = datetime(2026, 10, 14, tzinfo=UTC)


class PowerLoss(BaseException):
    pass


def invoke(tmp_path, client, remote, **extra):
    archive, key = files(tmp_path)
    return launch(
        client=client,
        remote=remote,
        source_archive=archive,
        ssh_key=key,
        source_commit="a" * 40,
        profile_digest="b" * 64,
        domain="woodkilldev.com",
        owner_cidr="8.8.4.4/32",
        run_id=RUN,
        probe_username="owner",
        probe_password="not-a-real-secret",
        state_root=tmp_path / "state",
        ssh_key_id=77,
        clock=extra.pop("clock", lambda: NOW),
        probe=lambda *a, **kw: {"ok": True, "routeCount": 8},
        **extra,
    )


def store(tmp_path):
    return FullPreviewLeaseStore(tmp_path / "state" / "leases")


def test_prepared_lease_exists_before_provider_create(tmp_path):
    client = Client()

    def interrupted(payload):
        lease = store(tmp_path).load(RUN)
        assert lease["state"] == "prepared" and lease["droplet"] is None
        raise PowerLoss()

    client.droplets.create = interrupted
    with pytest.raises(PowerLoss):
        invoke(tmp_path, client, Remote())


def test_schedule_failure_performs_zero_provider_mutations(tmp_path):
    client = Client()

    def failed_schedule(lease):
        assert store(tmp_path).load(RUN)["state"] == "prepared"
        raise RuntimeError("timer unavailable")

    with pytest.raises(RuntimeError, match="timer unavailable"):
        invoke(tmp_path, client, Remote(), schedule=failed_schedule)
    assert client.droplets.row is None and client.droplets.deleted == []


def test_compute_identity_is_durable_before_deploy(tmp_path):
    class Interrupted(Remote):
        def deploy(self, address, config):
            lease = store(tmp_path).load(RUN)
            assert lease["state"] == "compute-bound"
            assert lease["droplet"]["id"] == "123"
            raise PowerLoss()

    with pytest.raises(PowerLoss):
        invoke(tmp_path, Client(), Interrupted())
    assert store(tmp_path).load(RUN)["expiresAt"] == "2026-10-14T01:00:00Z"


def test_existing_lease_blocks_recreate_even_without_inventory(tmp_path):
    client = Client()
    invoke(tmp_path, client, Remote())
    client.droplets.row = None
    with pytest.raises(LeaseV2Conflict):
        invoke(tmp_path, client, Remote())
    assert client.droplets.row is None
    assert client.droplets.deleted == []


def test_unbound_owned_inventory_cannot_be_reported_destroyed(tmp_path):
    client = Client()
    invoke(tmp_path, client, Remote())
    lease = store(tmp_path).load(RUN)
    lease.update(state="prepared", droplet=None, dnsRecords=[])
    store(tmp_path).replace(lease)

    class Ambiguous:
        def list_owned_droplets(self, run_id):
            return [{"id": "unknown"}]

    with pytest.raises(LeaseV2Conflict, match="unbound"):
        teardown_full_preview(store(tmp_path), Ambiguous(), RUN, now=NOW + timedelta(hours=2))
    assert store(tmp_path).load(RUN)["state"] == "blocked"


def test_failed_launch_retains_sanitized_diagnostic(tmp_path):
    class Failed(Remote):
        def deploy(self, address, config):
            raise RuntimeError("private-value-must-not-be-persisted")

    client = Client()
    with pytest.raises(RuntimeError):
        invoke(tmp_path, client, Failed())
    lease = store(tmp_path).load(RUN)
    assert lease["state"] == "blocked"
    assert lease["lastError"] == "RuntimeError"
    assert "private-value" not in str(lease)
    assert client.droplets.deleted == [123]


def test_lost_create_response_preserves_prepared_identity_for_reconciliation(tmp_path):
    client = Client()
    create = client.droplets.create

    def lost_response(payload):
        create(payload)
        raise PowerLoss()

    client.droplets.create = lost_response
    with pytest.raises(PowerLoss):
        invoke(tmp_path, client, Remote())
    lease = store(tmp_path).load(RUN)
    assert lease["state"] == "prepared" and lease["droplet"] is None
    assert client.droplets.row["id"] == 123
    assert client.droplets.deleted == []


def test_cleanup_failure_keeps_bound_identity_and_original_failure(tmp_path):
    class Failed(Remote):
        def deploy(self, address, config):
            raise ValueError("private-original")

    client = Client()

    def deletion_failed(provider_id):
        raise RuntimeError("private-cleanup")

    client.droplets.delete = deletion_failed
    with pytest.raises(RuntimeError, match="cleanup requires reconciliation") as failure:
        invoke(tmp_path, client, Failed())
    assert isinstance(failure.value.__cause__, ValueError)
    lease = store(tmp_path).load(RUN)
    assert lease["state"] == "blocked" and lease["droplet"]["id"] == "123"
    assert lease["lastError"] == "ValueError"
    assert "private-" not in str(lease)


def test_malformed_create_identity_never_authorizes_deletion(tmp_path):
    client = Client()
    client.droplets.create = lambda payload: {"droplet": {"id": 999, "tags": []}}
    with pytest.raises(RuntimeError):
        invoke(tmp_path, client, Remote())
    assert client.droplets.deleted == []
    assert store(tmp_path).load(RUN)["droplet"] is None


def test_identity_drift_on_failure_never_authorizes_deletion(tmp_path):
    client = Client()

    class Failed(Remote):
        def deploy(self, address, config):
            client.droplets.row["name"] = "unrelated-resource"
            raise RuntimeError("deploy failed")

    with pytest.raises(RuntimeError, match="cleanup requires reconciliation"):
        invoke(tmp_path, client, Failed())
    assert client.droplets.deleted == []


def test_dns_receipt_is_bound_before_public_probe(tmp_path):
    client = Client()
    # invoke supplies its own probe; call launch with an explicit interruption.
    archive, key = files(tmp_path)

    def interrupted(*args, **kwargs):
        lease = store(tmp_path).load(RUN)
        assert lease["state"] == "dns-bound"
        assert len(lease["dnsRecords"]) == 6
        raise PowerLoss()

    with pytest.raises(PowerLoss):
        launch(
            client=client,
            remote=Remote(),
            source_archive=archive,
            ssh_key=key,
            source_commit="a" * 40,
            profile_digest="b" * 64,
            domain="woodkilldev.com",
            owner_cidr="8.8.4.4/32",
            run_id=RUN,
            probe_username="owner",
            probe_password="not-a-real-secret",
            state_root=tmp_path / "state",
            ssh_key_id=77,
            clock=lambda: NOW,
            probe=interrupted,
        )


def test_interrupted_dns_mutation_blocks_false_teardown_success(tmp_path):
    client = Client()
    create = client.domains.create_record

    def interrupted(domain, payload):
        create(domain, payload)
        raise PowerLoss()

    client.domains.create_record = interrupted
    with pytest.raises(PowerLoss):
        invoke(tmp_path, client, Remote())
    with pytest.raises(LeaseV2Conflict, match="DNS reconciliation"):
        teardown_full_preview(store(tmp_path), object(), RUN, now=NOW + timedelta(hours=2))
    assert store(tmp_path).load(RUN)["state"] != "destroyed"


def test_cli_failure_does_not_print_provider_secret(monkeypatch, capsys):
    from digital_ocean.scripts.python import full_preview_cli, full_preview_live

    def fail(args):
        raise RuntimeError("private-provider-value")

    monkeypatch.setattr(full_preview_live, "_main", fail)
    assert full_preview_cli.main(["launch"]) == 2
    output = capsys.readouterr()
    assert "private-provider-value" not in output.out + output.err
    assert "RuntimeError" in output.out
