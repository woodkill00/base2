#!/usr/bin/env python3
"""Bounded single-run cleanup controller for expired preview leases."""

from __future__ import annotations

import fcntl
import os
import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

try:
    from digital_ocean.scripts.python.preview_lease import LeaseStore
except ModuleNotFoundError:
    from preview_lease import LeaseStore


class SweeperBusy(RuntimeError):
    pass


@contextmanager
def _single_run(path: Path):
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SweeperBusy("preview sweeper is already running") from exc
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def sweep(
    store: LeaseStore,
    teardown: Callable[[str], None],
    notify: Callable[[dict], None],
    *,
    now: datetime | None = None,
    attempts: int = 3,
    backoff_seconds: tuple[float, ...] = (1.0, 2.0),
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    if attempts < 1 or len(backoff_seconds) < attempts - 1:
        raise ValueError("sweeper retry policy is invalid")
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    with _single_run(store.root / ".sweeper.lock"):
        due = store.reconcile_expired(now=current_time)
        completed: list[str] = []
        failed: list[str] = []
        for lease_id in due:
            for attempt in range(1, attempts + 1):
                try:
                    teardown(lease_id)
                    completed.append(lease_id)
                    break
                except Exception:
                    if attempt == attempts:
                        failed.append(lease_id)
                        notify(
                            {
                                "schemaVersion": 1,
                                "code": "preview_teardown_exhausted",
                                "leaseId": lease_id,
                                "attempts": attempts,
                            }
                        )
                    else:
                        sleep(backoff_seconds[attempt - 1])
        return {
            "schemaVersion": 1,
            "status": "failed" if failed else "passed",
            "due": due,
            "completed": completed,
            "failed": failed,
        }
