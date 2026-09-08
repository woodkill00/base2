from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.python.ephemeral_expiry import (
    ADAPTER,
    EphemeralExpiryError,
    ExpiryPlanStore,
    scan_due,
)

NOW = datetime(2026, 9, 8, tzinfo=UTC)
KEY = b"k" * 32


def _plan(deadline=NOW):
    return {
        "schemaVersion": 1,
        "planId": "preview-106-trial",
        "adapter": ADAPTER,
        "sourceCommit": "a" * 40,
        "expiresAt": deadline.isoformat(),
        "runId": "f106-trial",
        "stateRoot": "/home/base2/private/leases",
        "credentialFile": "/home/base2/private/do.json",
        "ownedResources": ["f106-trial"],
    }


def test_signed_durable_plan_waits_then_settles_and_replays_without_adapter(tmp_path):
    store = ExpiryPlanStore(tmp_path / "expiry", key=KEY)
    store.register(_plan(NOW + timedelta(minutes=5)))
    calls = []

    def adapter(plan):
        calls.append(plan["ownedResources"])
        return {"state": "destroyed", "runId": plan["runId"], "secretValuesEmitted": 0}

    waiting = scan_due(store, now=NOW, adapters={ADAPTER: adapter})
    assert waiting["pending"] == ["preview-106-trial"] and calls == []
    completed = scan_due(store, now=NOW + timedelta(minutes=6), adapters={ADAPTER: adapter})
    assert completed["destroyed"] == ["preview-106-trial"]
    assert calls == [["f106-trial"]]
    replay = scan_due(store, now=NOW + timedelta(minutes=7), adapters={ADAPTER: adapter})
    assert replay["replayed"] == ["preview-106-trial"]
    assert len(calls) == 1


def test_tampered_plan_unknown_adapter_and_nonterminal_receipt_fail_closed(tmp_path):
    store = ExpiryPlanStore(tmp_path / "expiry", key=KEY)
    signed = store.register(_plan())
    path = store.plan_root / "preview-106-trial.json"
    path.write_text(path.read_text().replace("a" * 40, "b" * 40, 1))
    with pytest.raises(EphemeralExpiryError, match="integrity"):
        store.plans()
    path.unlink()
    invalid = {key: value for key, value in signed.items() if key != "signature"}
    invalid["adapter"] = "shell"
    with pytest.raises(EphemeralExpiryError, match="plan_invalid"):
        store.register(invalid)

    clean = ExpiryPlanStore(tmp_path / "clean", key=KEY)
    clean.register(_plan())
    result = scan_due(
        clean,
        now=NOW,
        adapters={ADAPTER: lambda _plan: {"state": "pending"}},
    )
    assert len(result["failed"]) == 1
    assert result["status"] == "degraded"
    assert not list(clean.receipt_root.glob("*.json"))
    assert len(list(clean.failure_root.glob("*.json"))) == 1


def test_plan_inventory_is_bounded_and_unsafe_members_are_rejected(tmp_path):
    store = ExpiryPlanStore(tmp_path / "expiry", key=KEY)
    unsafe = store.plan_root / "../plans/not_safe.json"
    unsafe.write_text("{}")
    unsafe.chmod(0o600)
    with pytest.raises(EphemeralExpiryError, match="unsafe_plan_member"):
        store.plans()


def test_registration_rejects_the_sixty_fifth_plan_without_poisoning_inventory(tmp_path):
    store = ExpiryPlanStore(tmp_path / "expiry", key=KEY)
    for index in range(64):
        plan = _plan()
        plan["planId"] = f"preview-capacity-{index:02d}"
        plan["runId"] = f"capacity-{index:02d}"
        plan["ownedResources"] = [plan["runId"]]
        store.register(plan)
    rejected = _plan()
    rejected["planId"] = "preview-capacity-overflow"
    rejected["runId"] = "capacity-overflow"
    rejected["ownedResources"] = [rejected["runId"]]
    with pytest.raises(EphemeralExpiryError, match="capacity_exceeded"):
        store.register(rejected)
    assert len(store.plans()) == 64


def test_bad_member_and_adapter_crash_are_isolated_from_later_due_plan(tmp_path):
    store = ExpiryPlanStore(tmp_path / "expiry", key=KEY)
    bad = _plan()
    bad["planId"] = "preview-106-bad"
    bad["runId"] = "f106-bad"
    bad["ownedResources"] = [bad["runId"]]
    store.register(bad)
    good = _plan()
    good["planId"] = "preview-106-good"
    good["runId"] = "f106-good"
    good["ownedResources"] = [good["runId"]]
    store.register(good)

    def adapter(plan):
        if plan["runId"] == "f106-bad":
            raise RuntimeError("untrusted adapter detail")
        return {"state": "destroyed", "runId": plan["runId"], "secretValuesEmitted": 0}

    result = scan_due(store, now=NOW, adapters={ADAPTER: adapter})
    assert result["destroyed"] == ["preview-106-good"]
    assert len(result["failed"]) == 1
    assert result["status"] == "degraded"


def test_concurrent_registration_serializes_capacity_admission(tmp_path):
    store = ExpiryPlanStore(tmp_path / "expiry", key=KEY)
    for index in range(60):
        plan = _plan()
        plan["planId"] = f"preview-existing-{index:02d}"
        plan["runId"] = f"existing-{index:02d}"
        plan["ownedResources"] = [plan["runId"]]
        store.register(plan)

    def register(index):
        plan = _plan()
        plan["planId"] = f"preview-contended-{index:02d}"
        plan["runId"] = f"contended-{index:02d}"
        plan["ownedResources"] = [plan["runId"]]
        try:
            store.register(plan)
            return "registered"
        except EphemeralExpiryError as exc:
            assert str(exc) == "expiry:plan_capacity_exceeded"
            return "rejected"

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(register, range(12)))
    assert results.count("registered") == 4
    assert results.count("rejected") == 8
    assert len(store.plans()) == 64


def test_persistent_scanner_unit_is_hardened_and_has_no_arbitrary_command_surface():
    root = Path(__file__).resolve().parents[2]
    service = (root / "digital_ocean/systemd/base2-ephemeral-expiry-scan.service").read_text()
    timer = (root / "digital_ocean/systemd/base2-ephemeral-expiry-scan.timer").read_text()
    assert "WorkingDirectory=/opt/base2/current" in service
    assert "/usr/bin/python3 /opt/base2/current/scripts/python/ephemeral_expiry.py" in service
    assert "NoNewPrivileges=yes" in service
    assert "ProtectSystem=strict" in service
    assert "Persistent=true" in timer
    assert "OnUnitActiveSec=1min" in timer
