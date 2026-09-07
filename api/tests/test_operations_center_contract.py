from datetime import datetime, timedelta, timezone

import pytest

from api.services.operations_center import (
    OperationsContractError,
    alert_schedule,
    canonical_dimensions,
    classify_health,
    incident_fingerprint,
    next_incident_state,
    objective_state,
    synthetic_result,
)

NOW = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)


def test_health_states_are_truthful_and_stale_wins():
    assert classify_health(enabled=False, muted=False, probe_state=None, observed_at=None, expires_at=None, now=NOW) == "disabled"
    assert classify_health(enabled=True, muted=True, probe_state=None, observed_at=None, expires_at=None, now=NOW) == "muted"
    assert classify_health(enabled=True, muted=False, probe_state=None, observed_at=None, expires_at=None, now=NOW) == "unknown"
    assert classify_health(enabled=True, muted=False, probe_state="healthy", observed_at=NOW - timedelta(minutes=2), expires_at=NOW - timedelta(minutes=1), now=NOW) == "stale"
    assert classify_health(enabled=True, muted=False, probe_state="degraded", observed_at=NOW, expires_at=NOW + timedelta(minutes=1), now=NOW) == "degraded"


def test_health_rejects_naive_or_impossible_time():
    with pytest.raises(OperationsContractError):
        classify_health(enabled=True, muted=False, probe_state="healthy", observed_at=NOW, expires_at=NOW, now=NOW)


def test_dimensions_reject_secrets_nested_and_unbounded_values():
    assert canonical_dimensions({"region": "test", "attempt": 1}) == {"attempt": 1, "region": "test"}
    for value in ({"password": "x"}, {"region": {}}, {"region": "x" * 201}):
        with pytest.raises(OperationsContractError):
            canonical_dimensions(value)


def test_synthetic_result_is_exact_source_bounded_and_deterministic():
    steps = [{"code": "page.loaded", "passed": True, "durationMs": 12}]
    first = synthetic_result(journey="anonymous.public_page", role="anonymous", source_commit="a" * 40, steps=steps)
    second = synthetic_result(journey="anonymous.public_page", role="anonymous", source_commit="a" * 40, steps=steps)
    assert first == second
    assert first["status"] == "passed"
    assert len(first["resultDigest"]) == 64


def test_synthetic_result_rejects_unknown_journey_and_extra_step_data():
    with pytest.raises(OperationsContractError):
        synthetic_result(journey="shell.execute", role="administrator", source_commit="a" * 40, steps=[{"code": "bad", "passed": True, "durationMs": 1}])
    with pytest.raises(OperationsContractError):
        synthetic_result(journey="member.login", role="member", source_commit="a" * 40, steps=[{"code": "login.pass", "passed": True, "durationMs": 1, "body": "secret"}])


def test_incident_identity_is_tenant_bound_and_replay_stable():
    one = incident_fingerprint(site_id="tenant-one", service_key="api.health", code="api.unavailable")
    assert one == incident_fingerprint(site_id="tenant-one", service_key="api.health", code="api.unavailable")
    assert one != incident_fingerprint(site_id="tenant-two", service_key="api.health", code="api.unavailable")


def test_incident_transition_handles_ack_recovery_and_recurrence():
    assert next_incident_state(prior=None, failing=True) == "firing"
    assert next_incident_state(prior="firing", failing=True, acknowledged=True) == "acknowledged"
    assert next_incident_state(prior="acknowledged", failing=False) == "resolved"
    assert next_incident_state(prior="resolved", failing=True) == "recurring"


def test_alerts_expire_stop_and_back_off_with_finite_attempts():
    assert alert_schedule(severity="high", attempts=0, maximum_attempts=5, now=NOW, expires_at=NOW)["status"] == "expired"
    assert alert_schedule(severity="high", attempts=5, maximum_attempts=5, now=NOW, expires_at=NOW + timedelta(hours=1))["status"] == "failed"
    due = alert_schedule(severity="critical", attempts=2, maximum_attempts=5, now=NOW, expires_at=NOW + timedelta(hours=1))
    assert due == {"status": "queued", "nextAttemptAt": (NOW + timedelta(seconds=60)).isoformat()}


def test_objective_state_has_met_risk_and_breach_states():
    assert objective_state(successful=999, total=1000, target=0.999, warning=0.995) == "met"
    assert objective_state(successful=996, total=1000, target=0.999, warning=0.995) == "at_risk"
    assert objective_state(successful=900, total=1000, target=0.999, warning=0.995) == "breached"


def test_objective_rejects_empty_or_impossible_windows():
    with pytest.raises(OperationsContractError):
        objective_state(successful=0, total=0, target=0.99, warning=0.9)
