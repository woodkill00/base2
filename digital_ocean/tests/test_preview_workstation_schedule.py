from types import SimpleNamespace

import pytest

from digital_ocean.scripts.python.preview_workstation_schedule import (
    ScheduleError,
    install_schedule,
    render_units,
)
from digital_ocean.tests.test_preview_lease_v2 import payload


def args(tmp_path):
    return dict(
        repo=tmp_path / "repo",
        python=tmp_path / "python",
        state_root=tmp_path / "leases",
        credential_file=tmp_path / "credential.json",
    )


def test_persistent_schedule_preserves_expiry_and_bounded_retry(tmp_path):
    units = render_units(payload(), **args(tmp_path))
    service, timer = units.values()
    assert "Persistent=true" in timer and "2026-08-26 01:00:00 UTC" in timer
    assert "RestartSec=60" in service and "StartLimitBurst=5" in service
    assert "--early-approved" not in service
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0)

    root = tmp_path / "units"
    receipt = install_schedule(payload(), unit_root=root, run=run, **args(tmp_path))
    assert receipt["requiresWorkstationOnline"]
    assert calls[-1][2:4] == ["is-active", "--quiet"]
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir())
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    # A new installer instance after restart re-arms the original calendar date.
    assert install_schedule(payload(), unit_root=root, run=run, **args(tmp_path)) == receipt
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


def test_activation_failure_blocks_admission(tmp_path):
    with pytest.raises(ScheduleError):
        install_schedule(
            payload(),
            unit_root=tmp_path / "units",
            run=lambda *a, **kw: SimpleNamespace(returncode=1),
            **args(tmp_path),
        )


@pytest.mark.parametrize("path", ["/tmp/x%h", "/tmp/x\nExecStart=bad", "relative", "/tmp/../etc"])
def test_unsafe_paths_rejected(tmp_path, path):
    values = args(tmp_path)
    values["repo"] = path
    with pytest.raises(ScheduleError):
        render_units(payload(), **values)


def test_existing_conflicting_unit_never_overwritten(tmp_path):
    root = tmp_path / "units"
    root.mkdir()
    name = next(iter(render_units(payload(), **args(tmp_path))))
    (root / name).write_text("preserve")
    with pytest.raises(ScheduleError):
        install_schedule(payload(), unit_root=root, **args(tmp_path))
    assert (root / name).read_text() == "preserve"
