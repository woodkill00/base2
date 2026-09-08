import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.python.runtime_governance import (
    RuntimeGovernanceError, append_audit, break_glass_status, claim_job,
    credential_rotation, notification_policy, redact, schedule_due, secret_reference,
    settle_job, validate_credential_inventory, verify_audit,
)

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)
KEY = b"a" * 32
ROOT = Path(__file__).resolve().parents[2]


def test_secret_refs_inventory_and_recursive_redaction_are_closed():
    assert secret_reference("vaultwarden://woodkill/base2#token")
    with pytest.raises(RuntimeGovernanceError):
        secret_reference("literal-secret")
    inventory = [{
        "class": "provider-api", "owner": "operator", "scope": "base2",
        "source": "vaultwarden-ref", "consumer": "release-adapter", "lifetimeSeconds": 3600,
        "rotation": "overlap", "revocation": "immediate", "recovery": "owner-renewal",
    }]
    assert validate_credential_inventory(inventory) == inventory
    assert redact({"nested": [{"authorization": "Bearer value"}], "safe": "ok"}) == {
        "nested": [{"authorization": "[REDACTED]"}], "safe": "ok"
    }
    assert len(validate_credential_inventory(json.loads(
        (ROOT / "shared/config/credential-inventory-v1.json").read_text()
    ))) == 4


def test_audit_chain_detects_mutation_reorder_and_deletion():
    first = append_audit([], {
        "tenantId": "tenant-one", "actorRef": "owner", "action": "job.create",
        "targetRef": "job-1", "outcome": "accepted", "occurredAt": NOW.isoformat(),
    }, KEY)
    second = append_audit([first], {
        "tenantId": "tenant-one", "actorRef": "worker", "action": "job.finish",
        "targetRef": "job-1", "outcome": "passed", "occurredAt": NOW.isoformat(),
    }, KEY)
    assert verify_audit([first, second], KEY)
    for changed in ([second, first], [{**first, "outcome": "failed"}, second], [second]):
        with pytest.raises(RuntimeGovernanceError, match="chain_invalid"):
            verify_audit(changed, KEY)


def test_job_lease_replay_crash_recovery_backoff_and_dead_letter():
    job = {"state": "queued", "attempts": 0, "maximumAttempts": 2}
    claimed = claim_job(job, worker="worker-one", now=NOW)
    assert claim_job(claimed, worker="worker-one", now=NOW) == claimed
    with pytest.raises(RuntimeGovernanceError, match="already_leased"):
        claim_job(claimed, worker="worker-two", now=NOW)
    recovered = claim_job(claimed, worker="worker-two", now=NOW + timedelta(minutes=2))
    assert recovered["attempts"] == 2
    assert settle_job(recovered, worker="worker-two", outcome="fail", now=NOW)["state"] == "dead_letter"


def test_scheduler_timezone_lateness_overlap_and_restart_are_deterministic():
    schedule = {
        "timezone": "Europe/Berlin", "nextRunAt": (NOW - timedelta(minutes=2)).isoformat(),
        "overlapPolicy": "forbid", "enabled": True,
    }
    assert schedule_due(schedule, now=NOW, running=True)["action"] == "defer"
    assert schedule_due(schedule, now=NOW, running=False) == {"action": "enqueue_once", "lateSeconds": 120}
    assert schedule_due(schedule, now=NOW, running=False) == schedule_due(schedule, now=NOW, running=False)


def test_mandatory_security_bypasses_quiet_and_provider_preferences():
    assert notification_policy(family="security", preference="disabled", quiet=True) == "immediate"
    assert notification_policy(family="product", preference="immediate", quiet=True) == "digest"
    assert notification_policy(family="product", preference="disabled", quiet=False) == "disabled"


def test_rotation_requires_consumer_readiness_and_break_glass_expires_into_review():
    assert credential_rotation(current_generation=1, action="begin", consumers_ready=False) == {
        "generation": 2, "state": "overlap", "restartRequired": False
    }
    with pytest.raises(RuntimeGovernanceError, match="consumer_not_ready"):
        credential_rotation(current_generation=2, action="promote", consumers_ready=False)
    grant = {
        "requesterRef": "operator-one", "approverRef": "owner-two",
        "expiresAt": (NOW + timedelta(minutes=5)).isoformat(), "revokedAt": None,
        "reviewedAt": None,
    }
    assert break_glass_status(grant, now=NOW) == "active"
    assert break_glass_status(grant, now=NOW + timedelta(minutes=6)) == "expired_review_required"
