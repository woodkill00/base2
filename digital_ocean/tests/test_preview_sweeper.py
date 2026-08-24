from __future__ import annotations

import fcntl
import os
from datetime import UTC, datetime, timedelta

import pytest

from digital_ocean.scripts.python.preview_lease import LeaseStore
from digital_ocean.scripts.python.preview_sweeper import SweeperBusy, sweep

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def lease(lease_id="lease-sweep-001", *, expires=None):
    return {
        "schemaVersion": 1,
        "leaseId": lease_id,
        "siteId": "base2-test",
        "sourceCommit": "a" * 40,
        "manifestDigest": "b" * 64,
        "owner": "owner:test",
        "state": "planned",
        "createdAt": "2026-08-24T18:00:00Z",
        "expiresAt": (expires or (NOW + timedelta(hours=1))).isoformat().replace("+00:00", "Z"),
        "costPolicy": {"currency": "USD", "maximumMinorUnits": 100},
        "resources": [],
        "dnsMutations": [],
    }


def test_no_active_or_due_lease_is_clean_noop(tmp_path):
    store = LeaseStore(tmp_path)
    calls = []
    assert sweep(store, calls.append, calls.append, now=NOW)["due"] == []
    store.create(lease())
    assert sweep(store, calls.append, calls.append, now=NOW)["due"] == []
    assert calls == []


def test_absolute_expiry_calls_exact_teardown_once(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease(expires=NOW - timedelta(seconds=1)))
    calls = []
    result = sweep(store, calls.append, lambda _item: None, now=NOW)
    assert result["completed"] == ["lease-sweep-001"]
    assert calls == ["lease-sweep-001"]
    assert store.load("lease-sweep-001")["state"] == "teardown_due"


def test_idle_expiry_precedes_absolute_ttl(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease())
    store.touch_activity(
        "lease-sweep-001", now=NOW - timedelta(hours=1), idle_timeout=timedelta(minutes=30)
    )
    calls = []
    assert sweep(store, calls.append, lambda _item: None, now=NOW)["due"] == ["lease-sweep-001"]


def test_bounded_retry_backoff_and_single_notification(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease(expires=NOW - timedelta(seconds=1)))
    calls, delays, notifications = [], [], []

    def fail(lease_id):
        calls.append(lease_id)
        raise RuntimeError("provider secret detail")

    result = sweep(store, fail, notifications.append, now=NOW, sleep=delays.append)
    assert result["status"] == "failed"
    assert calls == ["lease-sweep-001"] * 3
    assert delays == [1.0, 2.0]
    assert notifications == [
        {
            "schemaVersion": 1,
            "code": "preview_teardown_exhausted",
            "leaseId": "lease-sweep-001",
            "attempts": 3,
        }
    ]
    assert "secret" not in str(notifications)


def test_transient_failure_recovers_without_notification(tmp_path):
    store = LeaseStore(tmp_path)
    store.create(lease(expires=NOW - timedelta(seconds=1)))
    attempts, notifications = [], []

    def transient(lease_id):
        attempts.append(lease_id)
        if len(attempts) == 1:
            raise RuntimeError("retry")

    result = sweep(store, transient, notifications.append, now=NOW, sleep=lambda _delay: None)
    assert result["status"] == "passed"
    assert attempts == ["lease-sweep-001", "lease-sweep-001"]
    assert notifications == []


def test_overlapping_sweeper_fails_fast_without_work(tmp_path):
    store = LeaseStore(tmp_path)
    descriptor = os.open(store.root / ".sweeper.lock", os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(SweeperBusy, match="already running"):
            sweep(store, lambda _lease: None, lambda _notice: None, now=NOW)
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
