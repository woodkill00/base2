from datetime import UTC, datetime, timedelta

import pytest

from scripts.python.ephemeral_expiry import (
    ADAPTER,
    EphemeralExpiryError,
    ExpiryPlanStore,
    scan_due,
)
from pathlib import Path

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
    with pytest.raises(EphemeralExpiryError, match="adapter_not_terminal"):
        scan_due(
            clean,
            now=NOW,
            adapters={ADAPTER: lambda _plan: {"state": "pending"}},
        )
    assert not list(clean.receipt_root.glob("*.json"))


def test_plan_inventory_is_bounded_and_unsafe_members_are_rejected(tmp_path):
    store = ExpiryPlanStore(tmp_path / "expiry", key=KEY)
    unsafe = store.plan_root / "../plans/not_safe.json"
    unsafe.write_text("{}")
    unsafe.chmod(0o600)
    with pytest.raises(EphemeralExpiryError, match="unsafe_plan_member"):
        store.plans()


def test_persistent_scanner_unit_is_hardened_and_has_no_arbitrary_command_surface():
    root = Path(__file__).resolve().parents[2]
    service = (root / "digital_ocean/systemd/base2-ephemeral-expiry-scan.service").read_text()
    timer = (root / "digital_ocean/systemd/base2-ephemeral-expiry-scan.timer").read_text()
    assert "scripts.python.ephemeral_expiry" in service
    assert "NoNewPrivileges=yes" in service
    assert "ProtectSystem=strict" in service
    assert "Persistent=true" in timer
    assert "OnUnitActiveSec=1min" in timer
