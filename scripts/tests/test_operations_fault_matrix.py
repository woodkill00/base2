from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from api.services.operations_center import (
    OperationsContractError,
    alert_schedule,
    classify_health,
    collect_probe_results,
    deliver_sanitized_alert,
    next_incident_state,
    sanitized_alert,
)
from scripts.python.operations_telemetry import AlertLedger

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def catalog():
    kinds = (
        "http",
        "database",
        "worker",
        "queue",
        "object-storage",
        "dns",
        "certificate",
        "email",
        "schedule",
        "capacity",
        "monitor",
        "backup",
        "restore",
        "migration",
    )
    return {
        "schemaVersion": 1,
        "probes": [
            {
                "id": f'{kind.replace("-", ".")}.probe',
                "kind": kind,
                "freshnessSeconds": 60,
                "timeoutSeconds": 1,
            }
            for kind in kinds
        ],
        "collection": {
            "maximumProbes": 32,
            "maximumBatchSeconds": 60,
            "maximumDimensions": 16,
        },
        "retention": {"healthDays": 30, "syntheticDays": 30, "incidentDays": 365},
    }


def test_monitor_and_dependency_loss_are_visible_without_false_health():
    results = collect_probe_results(
        catalog=catalog(),
        adapters={
            "http.probe": lambda _timeout: ("healthy", "http.ready", 1),
            "database.probe": lambda _timeout: (_ for _ in ()).throw(TimeoutError()),
        },
        now=NOW,
    )
    indexed = {item["probeId"]: item for item in results}
    assert indexed["database.probe"]["state"] == "unavailable"
    assert indexed["monitor.probe"]["state"] == "unknown"
    assert indexed["http.probe"]["state"] == "healthy"


def test_stale_clock_shift_and_flapping_have_truthful_bounded_states():
    assert (
        classify_health(
            enabled=True,
            muted=False,
            probe_state="healthy",
            observed_at=NOW - timedelta(minutes=2),
            expires_at=NOW - timedelta(minutes=1),
            now=NOW,
        )
        == "stale"
    )
    with pytest.raises(OperationsContractError, match="timezone"):
        classify_health(
            enabled=True,
            muted=False,
            probe_state="healthy",
            observed_at=NOW,
            expires_at=NOW + timedelta(minutes=1),
            now=datetime(2026, 9, 8),
        )
    states = []
    prior = None
    for failing in (True, False, True, True, False):
        prior = next_incident_state(prior=prior, failing=failing)
        states.append(prior)
    assert states == ["firing", "resolved", "recurring", "recurring", "resolved"]


def test_alert_outage_queues_once_and_recovery_does_not_storm():
    payload = sanitized_alert(
        incident_id="a" * 64,
        severity="critical",
        summary_code="monitor.unavailable",
        expires_at=NOW + timedelta(minutes=15),
    )
    assert (
        deliver_sanitized_alert(
            payload=payload,
            now=NOW,
            sender=lambda _item: (_ for _ in ()).throw(ConnectionError()),
        )["status"]
        == "queued"
    )
    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "alerts.json"
        first = AlertLedger(path).observe(
            incident_id="incident-monitor-001", failing=True, code="monitor.failed"
        )
        restarted = AlertLedger(path)
        duplicate = restarted.observe(
            incident_id="incident-monitor-001", failing=True, code="monitor.failed"
        )
        recovered = restarted.observe(
            incident_id="incident-monitor-001", failing=False, code="monitor.recovered"
        )
        assert [first["notify"], duplicate["notify"], recovered["notify"]] == [True, False, True]


def test_queue_pressure_exhaustion_and_expiry_stop_retrying():
    expires = NOW + timedelta(hours=1)
    assert alert_schedule(
        severity="high", attempts=5, maximum_attempts=5, now=NOW, expires_at=expires
    ) == {"status": "failed", "nextAttemptAt": None}
    assert alert_schedule(
        severity="high",
        attempts=0,
        maximum_attempts=5,
        now=expires,
        expires_at=expires,
    ) == {"status": "expired", "nextAttemptAt": None}
