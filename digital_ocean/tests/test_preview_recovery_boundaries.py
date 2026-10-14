import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from digital_ocean.scripts.python import full_preview_expire as expiry
from digital_ocean.scripts.python.full_preview_cli import main as cli
from digital_ocean.scripts.python.preview_workstation_schedule import render_units
from digital_ocean.tests.test_preview_lease_v2 import payload
from digital_ocean.tests.test_preview_startup_recovery import (
    NOW,
    RUN,
    Client,
    Remote,
    invoke,
    store,
)


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"droplets": None},
        {"droplets": ["bad"]},
        {"droplets": [], "links": {"pages": {"next": "more"}}},
    ],
)
def test_incomplete_inventory_never_admits_launch(tmp_path, response):
    client = Client()
    client.droplets.list = lambda **kw: response
    with pytest.raises(expiry.ExpiryError):
        invoke(tmp_path, client, Remote())
    assert client.droplets.row is None and client.droplets.deleted == []


def test_periodic_timer_survives_busy_window_and_stops_after_terminal_success(
    tmp_path, monkeypatch, capsys
):
    client = Client()
    invoke(tmp_path, client, Remote())
    lease = store(tmp_path).load(RUN)
    lease["state"] = "destroyed"
    store(tmp_path).replace(lease)
    commands = []
    monkeypatch.setattr(
        expiry.subprocess,
        "run",
        lambda argv, **kw: commands.append(argv) or SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        expiry, "_token", lambda path: (_ for _ in ()).throw(AssertionError("no credential read"))
    )
    assert (
        expiry.main(
            [
                "--state-root",
                str(store(tmp_path).root),
                "--run-id",
                RUN,
                "--credential-file",
                "unused",
                "--stop-timer-on-success",
            ]
        )
        == 0
    )
    assert commands == [
        ["systemctl", "--user", "disable", "--now", f"base2-preview-{RUN}-expiry.timer"]
    ]
    assert json.loads(capsys.readouterr().out)["mutationSent"] is False
    units = render_units(
        payload(),
        repo=tmp_path,
        python=tmp_path / "python",
        state_root=tmp_path,
        credential_file=tmp_path / "private.json",
    )
    assert "OnUnitInactiveSec=60" in next(
        value for name, value in units.items() if name.endswith(".timer")
    )


def test_reconciliation_cli_is_read_only(tmp_path, monkeypatch, capsys):
    client = Client()
    invoke(tmp_path, client, Remote())
    before = list(client.domains.rows)
    monkeypatch.setattr(expiry, "_token", lambda path: "synthetic")
    monkeypatch.setattr(expiry, "DigitalOceanHttpClient", lambda token: client)
    assert (
        cli(
            [
                "reconcile",
                "--reconcile",
                RUN,
                "--domain",
                "woodkilldev.com",
                "--state-root",
                str(store(tmp_path).root),
                "--credential-file",
                "unused",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["computeCandidateIds"] == ["123"] and result["mutationSent"] is False
    assert client.droplets.deleted == [] and client.domains.rows == before


def test_schedule_delay_past_expiry_never_creates_compute(tmp_path):
    time = [NOW]

    def delayed(lease):
        time[0] += timedelta(hours=2)

    client = Client()
    with pytest.raises(RuntimeError, match="expired during launch"):
        invoke(tmp_path, client, Remote(), clock=lambda: time[0], schedule=delayed)
    assert client.droplets.row is None and client.droplets.deleted == []


def test_slow_deployment_past_expiry_is_not_published(tmp_path):
    time = [NOW]

    class Slow(Remote):
        def deploy(self, address, config):
            time[0] += timedelta(hours=2)

    client = Client()
    with pytest.raises(RuntimeError, match="expired during launch"):
        invoke(tmp_path, client, Slow(), clock=lambda: time[0])
    assert client.droplets.deleted == [123]
    assert len(client.domains.rows) == 1  # original DNS was never replaced
