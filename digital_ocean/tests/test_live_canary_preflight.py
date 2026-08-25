from __future__ import annotations

import json
import hashlib
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from digital_ocean.scripts.python import live_canary_preflight


def write_env(path: Path, **overrides) -> Path:
    values = {
        "PROJECT_NAME": "base2",
        "WEBSITE_DOMAIN": "example.com",
        "DO_DOMAIN": "${WEBSITE_DOMAIN}",
        "DO_API_REGION": "nyc3",
        "DO_API_SIZE": "s-1vcpu-1gb",
        "DO_API_IMAGE": "ubuntu-24-04-x64",
        "DO_CANARY_HOURLY_COST_MINOR_UNITS_CEILING": "4",
        "DO_API_TOKEN": "must-never-appear",
    }
    values.update(overrides)
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    return path


def exact_commit(monkeypatch):
    def fake_run(args, **_kwargs):
        if args[1] == "rev-parse":
            return CompletedProcess(args, 0, stdout="a" * 40 + "\n")
        return CompletedProcess(args, 0, stdout=b"exact-archive")

    monkeypatch.setattr(live_canary_preflight.subprocess, "run", fake_run)


def test_plan_is_exact_minimal_redacted_and_networkless(monkeypatch, tmp_path):
    exact_commit(monkeypatch)
    env = write_env(tmp_path / ".env")
    monkeypatch.setattr(
        "socket.socket",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network attempted")),
    )
    plan = live_canary_preflight.build_plan(env, tmp_path)
    rendered = json.dumps(plan)
    assert "must-never-appear" not in rendered
    assert plan["credentialConfigured"] is True
    assert plan["dnsMutations"] == [
        {"name": "f093-aaaaaaaa", "type": "A", "fqdn": "f093-aaaaaaaa.example.com"}
    ]
    assert plan["certificateSans"] == ["f093-aaaaaaaa.example.com"]
    assert plan["sourceArchiveSha256"] == hashlib.sha256(b"exact-archive").hexdigest()
    assert plan["ownershipNamespace"] == "base2-f093-aaaaaaaa"
    assert plan["maximumConcurrentDroplets"] == 1
    assert plan["totalCostCeilingMinorUnits"] == 100
    assert plan["hourlyCostMinorUnitsCeiling"] == 4
    assert plan["certificateMode"] == "letsencrypt-staging-only"
    assert plan["networkRequests"] == 0


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"PROJECT_NAME": "../bad"}, "project name"),
        ({"WEBSITE_DOMAIN": "example.invalid"}, "public DNS zone"),
        ({"DO_API_REGION": "../bad"}, "region"),
    ],
)
def test_unsafe_or_non_public_targets_fail_closed(monkeypatch, tmp_path, overrides, message):
    exact_commit(monkeypatch)
    env = write_env(tmp_path / ".env", **overrides)
    with pytest.raises(live_canary_preflight.PreflightError, match=message):
        live_canary_preflight.build_plan(env, tmp_path)


def test_symlink_environment_and_non_exact_commit_fail_closed(monkeypatch, tmp_path):
    real = write_env(tmp_path / "real.env")
    link = tmp_path / "linked.env"
    link.symlink_to(real)
    exact_commit(monkeypatch)
    with pytest.raises(live_canary_preflight.PreflightError, match="real file"):
        live_canary_preflight.build_plan(link, tmp_path)
    monkeypatch.setattr(
        live_canary_preflight.subprocess,
        "run",
        lambda args, **_kwargs: CompletedProcess(args, 0, stdout="not-exact\n"),
    )
    with pytest.raises(live_canary_preflight.PreflightError, match="exact lowercase"):
        live_canary_preflight.build_plan(real, tmp_path)


def test_cli_emits_machine_readable_plan(monkeypatch, tmp_path, capsys):
    exact_commit(monkeypatch)
    env = write_env(tmp_path / ".env")
    assert (
        live_canary_preflight.main(
            ["--env-path", str(env), "--repo-root", str(tmp_path)]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "approval-required"
