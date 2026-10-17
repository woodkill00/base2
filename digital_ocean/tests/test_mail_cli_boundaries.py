import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from digital_ocean.tests.test_persistent_mail_dns import CONFIG, Provider


@pytest.mark.parametrize(
    "mode", ["plan", "apply", "bad-delegation", "conflict", "provider-failure"]
)
def test_dns_cli_sanitizes_failure_and_bounds_writes(tmp_path, monkeypatch, capsys, mode):
    from digital_ocean.scripts.python.persistent_mail_dns import main

    provider = Provider()
    if mode == "conflict":
        provider.rows = [{"type": "TXT", "name": "_dmarc", "data": "v=DMARC1; p=reject;"}]
    if mode == "provider-failure":

        def fail(_):
            raise RuntimeError("private credential must not appear")

        provider.list_records = fail
    names = ["ns1.digitalocean.com.", "ns2.digitalocean.com.", "ns3.digitalocean.com."]
    if mode == "bad-delegation":
        names = ["ns.other.example."]
    response = json.dumps(
        {"Status": 0, "Answer": [{"type": 2, "data": name} for name in names]}
    ).encode()
    monkeypatch.setattr(
        "urllib.request.build_opener",
        lambda *args: SimpleNamespace(open=lambda *args, **kwargs: io.BytesIO(response)),
    )
    monkeypatch.setattr(
        "digital_ocean.scripts.python.full_preview_expire._token", lambda _: "fixture"
    )
    monkeypatch.setattr(
        "digital_ocean.scripts.python.live_preview_provider.DigitalOceanHttpClient",
        lambda _: SimpleNamespace(domains=provider),
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    args = [
        "--config",
        str(CONFIG),
        "--credential-file",
        str(tmp_path / "unused"),
        "--state-root",
        str(tmp_path / "state"),
    ]
    if mode == "apply":
        args.append("--apply")
    assert main(args) == (0 if mode in {"plan", "apply"} else 2)
    assert provider.calls == (4 if mode == "apply" else 0)
    assert "private credential" not in capsys.readouterr().out


@pytest.mark.parametrize("fail", [False, True])
def test_trial_cli_keeps_handoff_on_failure(tmp_path, monkeypatch, capsys, fail):
    import sys

    from digital_ocean.scripts.python import mail_trial_config as module

    source = tmp_path / "input"
    source.write_text("synthetic")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trial",
            "--input",
            str(source),
            "--env-file",
            str(tmp_path / ".env"),
            "--state-root",
            str(tmp_path / "state"),
            "--domain",
            "woodkilldev.com",
        ],
    )

    def configure(*args, **kwargs):
        if fail:
            raise RuntimeError("private secret must not be printed")

    monkeypatch.setattr(module, "configure_trial", configure)
    if fail:
        with pytest.raises(SystemExit, match="mail_trial_configuration_failed"):
            module.main()
        assert source.exists()
    else:
        module.main()
        assert not source.exists()
    assert "private secret" not in capsys.readouterr().out
