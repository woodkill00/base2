"""No provider access while another lifecycle operation owns the lease root."""

import multiprocessing
import os
from datetime import timedelta

import pytest

from digital_ocean.scripts.python.preview_lease_v2 import (
    FullPreviewLeaseStore,
    LeaseV2Conflict,
    LeaseV2IntegrityError,
    teardown_full_preview,
)
from digital_ocean.tests.test_preview_startup_recovery import (
    NOW,
    RUN,
    Client,
    PowerLoss,
    Remote,
    invoke,
    store,
)


def test_launch_rejects_competing_launch_and_expiry_before_provider_access(tmp_path):
    class DuringLaunch(Remote):
        def deploy(self, address, config):
            with pytest.raises(LeaseV2Conflict, match="operation busy"):
                teardown_full_preview(store(tmp_path), object(), RUN, now=NOW + timedelta(hours=2))
            with pytest.raises(LeaseV2Conflict, match="operation busy"):
                invoke(tmp_path, object(), Remote())

    invoke(tmp_path, Client(), DuringLaunch())
    assert store(tmp_path).load(RUN)["state"] == "live-verified"


def test_interruption_releases_operation_lock(tmp_path):
    class Interrupted(Remote):
        def deploy(self, address, config):
            raise PowerLoss()

    with pytest.raises(PowerLoss):
        invoke(tmp_path, Client(), Interrupted())
    with store(tmp_path).operation():
        assert store(tmp_path).load(RUN)["state"] == "compute-bound"


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "public"])
def test_unsafe_operation_lock_rejected_without_touching_target(tmp_path, kind):
    lease_store = FullPreviewLeaseStore(tmp_path / "leases")
    target = tmp_path / "target"
    target.write_text("preserve")
    target.chmod(0o600)
    lock = lease_store.root / ".operation.lock"
    if kind == "symlink":
        lock.symlink_to(target)
    elif kind == "hardlink":
        os.link(target, lock)
    else:
        lock.write_text("preserve")
        lock.chmod(0o644)
    with pytest.raises(LeaseV2IntegrityError), lease_store.operation():
        pytest.fail("unsafe lock was admitted")
    assert target.read_text() == "preserve"


def test_separate_store_instances_share_nonblocking_lock(tmp_path):
    first = FullPreviewLeaseStore(tmp_path)
    second = FullPreviewLeaseStore(tmp_path)
    with (
        first.operation(),
        pytest.raises(LeaseV2Conflict, match="operation busy"),
        second.operation(),
    ):
        pytest.fail("second owner entered")
    with second.operation():
        pass


def _hold_lock(path, ready):
    with FullPreviewLeaseStore(path).operation():
        ready.set()
        multiprocessing.Event().wait(20)


def test_killed_process_releases_kernel_lock(tmp_path):
    context = multiprocessing.get_context("fork")
    ready = context.Event()
    process = context.Process(target=_hold_lock, args=(tmp_path, ready))
    process.start()
    try:
        assert ready.wait(5), "child never acquired operation lock"
        with (
            pytest.raises(LeaseV2Conflict, match="operation busy"),
            FullPreviewLeaseStore(tmp_path).operation(),
        ):
            pytest.fail("entered while child held lock")
    finally:
        process.terminate()
        process.join(5)
        if process.is_alive():
            process.kill()
            process.join(5)
    assert not process.is_alive()
    with FullPreviewLeaseStore(tmp_path).operation():
        pass
