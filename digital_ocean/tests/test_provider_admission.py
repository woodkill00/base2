from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Event, Thread

import pytest

from digital_ocean.scripts.python.provider_admission import (
    AdmissionDenied,
    AdmissionPolicy,
    AdmissionSnapshot,
    CircuitIntegrityError,
    ProviderAdmissionController,
)

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def snapshot(**changes):
    values = {
        "active_resources": 0,
        "provider_quota": 5,
        "projected_minor_units": 10,
        "budget_ceiling_minor_units": 100,
        "disk_free_bytes": 2_000,
        "memory_available_bytes": 2_000,
        "oom_kills": 0,
    }
    values.update(changes)
    return AdmissionSnapshot(**values)


def controller(tmp_path, *, clock=lambda: NOW, notifications=None, sleep=lambda _delay: None):
    notify = (
        notifications
        if callable(notifications)
        else (notifications if notifications is not None else []).append
    )
    return ProviderAdmissionController(
        tmp_path,
        AdmissionPolicy(
            maximum_active_resources=4,
            minimum_disk_free_bytes=1_000,
            minimum_memory_available_bytes=1_000,
            maximum_attempts=3,
            open_after_failures=2,
            cooldown=timedelta(minutes=5),
        ),
        clock=clock,
        notify=notify,
        sleep=sleep,
    )


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"active_resources": 4}, "resource_limit"),
        ({"active_resources": 5, "provider_quota": 5}, "provider_quota"),
        ({"projected_minor_units": 101}, "budget_ceiling"),
        ({"disk_free_bytes": 999}, "disk_pressure"),
        ({"memory_available_bytes": 999}, "memory_pressure"),
        ({"oom_kills": 1}, "oom_detected"),
    ],
)
def test_exhaustion_fails_before_provider_call(tmp_path, changes, code):
    calls = []
    control = controller(tmp_path)
    with pytest.raises(AdmissionDenied, match=code):
        control.execute("preview-create", snapshot(**changes), lambda: calls.append("called"))
    assert calls == []


def test_rate_limit_retries_are_bounded_then_circuit_blocks_storm(tmp_path):
    class RateLimited(RuntimeError):
        status_code = 429

    calls = []
    notifications = []
    control = controller(tmp_path, notifications=notifications)

    def fail():
        calls.append("called")
        raise RateLimited("provider detail must not be retained")

    with pytest.raises(RateLimited):
        control.execute("preview-create", snapshot(), fail)
    assert len(calls) == 3
    with pytest.raises(AdmissionDenied, match="circuit_open"):
        control.execute("preview-create", snapshot(), fail)
    assert len(calls) == 3
    assert notifications == [
        {
            "schemaVersion": 1,
            "code": "provider_circuit_open",
            "scope": "preview-create",
        }
    ]


def test_nonretryable_provider_failure_is_called_once(tmp_path):
    calls = []

    def fail():
        calls.append("called")
        raise RuntimeError("ordinary failure")

    with pytest.raises(RuntimeError, match="ordinary"):
        controller(tmp_path).execute("preview-create", snapshot(), fail)
    assert calls == ["called"]


def test_cooldown_allows_one_probe_and_success_closes_with_recovery_notice(tmp_path):
    class Unavailable(RuntimeError):
        status_code = 503

    moments = iter([NOW, NOW + timedelta(minutes=6)])
    notifications = []
    control = controller(tmp_path, clock=lambda: next(moments), notifications=notifications)
    with pytest.raises(Unavailable):
        control.execute("preview-create", snapshot(), lambda: (_ for _ in ()).throw(Unavailable()))
    assert control.execute("preview-create", snapshot(), lambda: "ok") == "ok"
    assert [item["code"] for item in notifications] == [
        "provider_circuit_open",
        "provider_circuit_recovered",
    ]
    assert control.status("preview-create")["state"] == "closed"


def test_half_open_circuit_allows_exactly_one_concurrent_probe(tmp_path):
    class Unavailable(RuntimeError):
        status_code = 503

    current = [NOW]
    control = controller(tmp_path, clock=lambda: current[0])
    with pytest.raises(Unavailable):
        control.execute("preview-create", snapshot(), lambda: (_ for _ in ()).throw(Unavailable()))
    current[0] = NOW + timedelta(minutes=6)
    started, release = Event(), Event()
    result = []

    def probe():
        result.append(
            control.execute(
                "preview-create",
                snapshot(),
                lambda: (started.set(), release.wait(timeout=2), "ok")[-1],
            )
        )

    thread = Thread(target=probe)
    thread.start()
    assert started.wait(timeout=2)
    with pytest.raises(AdmissionDenied, match="circuit_open"):
        control.execute("preview-create", snapshot(), lambda: "second")
    release.set()
    thread.join(timeout=2)
    assert result == ["ok"]


def test_notification_is_deduplicated_across_controller_restart(tmp_path):
    notifications = []
    first = controller(tmp_path, notifications=notifications)
    for _ in range(2):
        with pytest.raises(AdmissionDenied, match="disk_pressure"):
            first.execute("preview-create", snapshot(disk_free_bytes=1), lambda: None)
    second = controller(tmp_path, notifications=notifications)
    with pytest.raises(AdmissionDenied, match="disk_pressure"):
        second.execute("preview-create", snapshot(disk_free_bytes=1), lambda: None)
    assert [item["code"] for item in notifications] == ["admission_disk_pressure"]


def test_failed_notification_delivery_is_durable_and_retried_after_restart(tmp_path):
    def unavailable(_receipt):
        raise RuntimeError("discord unavailable")

    first = controller(tmp_path, notifications=unavailable)
    with pytest.raises(AdmissionDenied, match="disk_pressure"):
        first.execute("preview-create", snapshot(disk_free_bytes=1), lambda: None)
    assert first.status("preview-create")["pendingNotifications"] == ["admission_disk_pressure"]

    delivered = []
    second = controller(tmp_path, notifications=delivered)
    with pytest.raises(AdmissionDenied, match="disk_pressure"):
        second.execute("preview-create", snapshot(disk_free_bytes=1), lambda: None)
    assert [item["code"] for item in delivered] == ["admission_disk_pressure"]
    assert second.status("preview-create")["pendingNotifications"] == []


def test_corrupt_durable_circuit_state_fails_closed(tmp_path):
    control = controller(tmp_path)
    control.status("preview-create")
    path = tmp_path / "preview-create.json"
    path.write_text(path.read_text().replace('"state":"closed"', '"state":"open"'))
    with pytest.raises(CircuitIntegrityError):
        control.execute("preview-create", snapshot(), lambda: "unsafe")


def test_invalid_policy_and_snapshot_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        AdmissionPolicy(maximum_attempts=0)
    with pytest.raises(ValueError):
        controller(tmp_path).execute("preview-create", snapshot(active_resources=-1), lambda: None)
