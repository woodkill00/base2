import json
from datetime import UTC, datetime

import pytest

from digital_ocean.scripts.python import preview_browser_inputs as module
from digital_ocean.scripts.python.preview_browser_inputs import browser_environment, private_json


def receipt():
    return dict(
        ok=True,
        status="live-verified",
        runId="base2-full-20261015-120000",
        sourceCommit="a" * 40,
        profileId="base2-obsidian",
        publicIp="192.0.2.1",
        domain="woodkilldev.com",
        expiresAt="2026-10-15T13:00:00Z",
        previewMode="full",
    )


def build(value=None, owner=None):
    return browser_environment(
        value or receipt(),
        owner
        or dict(
            email="owner@example.test",
            password="synthetic-only",
            display_name="woodkill",
            profile="base2-obsidian",
        ),
        run_id=receipt()["runId"],
        source_commit="a" * 40,
        now=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )


def test_identity_from_private_inputs():
    env = build()
    assert env["BASE2_OWNER_EMAIL"] == "owner@example.test"
    assert env["BASE2_LIVE_SOURCE_COMMIT"] == "a" * 40
    assert env["BASE2_LIVE_RUN_ID"] == receipt()["runId"]


def test_supported_cli_dispatch(monkeypatch):
    from digital_ocean.scripts.python import full_preview_cli

    calls = []
    monkeypatch.setattr(module, "main", lambda args: calls.append(args) or 9)
    assert full_preview_cli.main(["browser", "--receipt", "private-input"]) == 9
    assert calls == [["--receipt", "private-input"]]


@pytest.mark.parametrize(
    "key,value",
    [
        ("ok", False),
        ("status", "destroyed"),
        ("runId", "../escape"),
        ("sourceCommit", "b" * 40),
        ("profileId", "other"),
        ("publicIp", "not-ip"),
        ("domain", "unapproved.test"),
        ("previewMode", "restricted"),
        ("expiresAt", "2026-10-15T11:00:00Z"),
        ("expiresAt", "invalid"),
    ],
)
def test_rejects_stale_or_wrong_receipt(key, value):
    data = receipt()
    data[key] = value
    with pytest.raises(ValueError):
        build(data)


@pytest.mark.parametrize(
    "owner", [{}, {"email": "not-email", "password": "secret", "profile": "other"}]
)
def test_invalid_owner(owner):
    with pytest.raises(ValueError):
        browser_environment(
            receipt(),
            owner,
            run_id=receipt()["runId"],
            source_commit="a" * 40,
            now=datetime(2026, 10, 15, 12, tzinfo=UTC),
        )


def test_private_file_safety(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(receipt()))
    path.chmod(0o600)
    assert private_json(path)["ok"] is True
    path.chmod(0o644)
    with pytest.raises(ValueError):
        private_json(path)
    path.chmod(0o600)
    linked = tmp_path / "link"
    linked.symlink_to(path)
    with pytest.raises(ValueError):
        private_json(linked)
    path.write_text("x" * 20000)
    with pytest.raises(ValueError):
        private_json(path)


def test_main_handoff_and_sanitized_failure(tmp_path, monkeypatch, capsys):
    from digital_ocean.scripts.python import preview_media_inputs
    monkeypatch.setattr(preview_media_inputs, 'provision_media_inputs', lambda **kw: {'BASE2_MEDIA_EMAIL': 'fixture@example.invalid', 'BASE2_MEDIA_PASSWORD': 'PRIVATE_FIXTURE'})
    monkeypatch.setattr(module, "current_lease", lambda *args: None)
    source = tmp_path / "receipt.json"
    source.write_text(json.dumps(receipt()))
    source.chmod(0o600)
    owner = tmp_path / "owner.json"
    owner.write_text(
        json.dumps(
            dict(
                email="owner@example.test",
                password="PRIVATE_TEST_VALUE",
                display_name="woodkill",
                profile="base2-obsidian",
            )
        )
    )
    owner.chmod(0o600)
    args = ["--receipt", str(source), "--owner-file", str(owner), "--run-id", receipt()["runId"], "--ssh-private-key", "/private/key"]
    monkeypatch.setattr(
        module.subprocess, "check_output", lambda cmd, **kw: b"" if "status" in cmd else "a" * 40
    )

    class Clock:
        @staticmethod
        def now(tz):
            return datetime(2026, 10, 15, 12, tzinfo=UTC)

        fromisoformat = datetime.fromisoformat

    monkeypatch.setattr(module, "datetime", Clock)
    calls = []

    def run(cmd, **kw):
        calls.append((cmd, kw))
        return type("Result", (), {"returncode": 7})()

    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.main(args) == 7
    assert calls[0][0] == ["npm", "run", "test:live-full-preview"]
    assert calls[0][1]["env"]["BASE2_OWNER_PASSWORD"] == "PRIVATE_TEST_VALUE"
    assert "PRIVATE_TEST_VALUE" not in capsys.readouterr().out
    monkeypatch.setattr(module.subprocess, "check_output", lambda *a, **kw: b"dirty")
    assert module.main(args) == 1
    assert len(calls) == 1
    assert "PRIVATE_TEST_VALUE" not in capsys.readouterr().out


def test_private_json_rejects_nonobject_and_hardlinks(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[]")
    path.chmod(0o600)
    with pytest.raises(ValueError):
        private_json(path)
    path.write_text("{}")
    linked = tmp_path / "hard"
    linked.hardlink_to(path)
    with pytest.raises(ValueError):
        private_json(path)


@pytest.mark.parametrize("failure", [None, "destroyed", "source", "address", "tamper", "missing"])
def test_current_durable_lease(tmp_path, failure):
    from digital_ocean.tests.test_preview_lease_v2 import payload

    data = receipt()
    run = data["runId"]
    root = tmp_path / run
    source = root / "evidence" / f"{run}.json"
    store = module.FullPreviewLeaseStore(root / "leases")
    lease = payload(runId=run, sourceCommit=data["sourceCommit"], expiresAt=data["expiresAt"])
    lease["droplet"]["tags"] = [run]
    lease["dnsRecords"][0]["value"] = data["publicIp"]
    if failure == "destroyed":
        lease["state"] = "destroyed"
    if failure == "source":
        lease["sourceCommit"] = "b" * 40
    if failure == "address":
        lease["dnsRecords"][0]["value"] = "192.0.2.2"
    store.create(lease)
    path = store.root / f"{run}.json"
    if failure == "tamper":
        path.write_text(path.read_text().replace("live-verified", "destroyed"))
    if failure == "missing":
        path.unlink()
    if failure:
        with pytest.raises((ValueError, OSError, module.LeaseV2IntegrityError)):
            module.current_lease(source, data, run)
    else:
        module.current_lease(source, data, run)


def test_failed_lease_never_reads_owner(monkeypatch, capsys):
    reads = []
    monkeypatch.setattr(
        module.subprocess, "check_output", lambda cmd, **kw: b"" if "status" in cmd else "a" * 40
    )
    monkeypatch.setattr(module, "private_json", lambda path: reads.append(path.name) or receipt())

    def reject(*args):
        raise module.LeaseV2IntegrityError("private diagnostic")

    monkeypatch.setattr(module, "current_lease", reject)
    assert (
        module.main(
            ["--receipt", "/receipt", "--owner-file", "/owner", "--run-id", receipt()["runId"], "--ssh-private-key", "/private/key"]
        )
        == 1
    )
    assert reads == ["receipt"]
    assert "private diagnostic" not in capsys.readouterr().out
