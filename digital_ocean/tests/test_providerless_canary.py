from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from digital_ocean.scripts.python import providerless_canary


def test_complete_providerless_lifecycle_has_zero_external_authority(monkeypatch):
    root = Path(__file__).resolve().parents[2]

    def forbidden_socket(*_args, **_kwargs):
        raise AssertionError("providerless canary attempted network access")

    monkeypatch.setattr("socket.socket", forbidden_socket)
    for key in ("DO_API_TOKEN", "DIGITALOCEAN_ACCESS_TOKEN", "CLOUDFLARE_API_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    result = providerless_canary.run_canary(root)
    assert result["status"] == "passed"
    assert result["networkRequests"] == 0
    assert result["credentialReads"] == 0
    assert result["externalProviderMutations"] == 0
    assert result["publicDnsMutations"] == 0
    assert result["productionCertificates"] == 0
    assert all(result["assertions"].values())


def test_cli_emits_one_machine_readable_receipt(capsys):
    root = Path(__file__).resolve().parents[2]
    assert providerless_canary.main(["--repo-root", str(root)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["provider"] == "in-memory-fixture"
    assert receipt["assertions"]["zeroProviderResources"] is True


def test_canary_rejects_non_exact_source_commit(monkeypatch, tmp_path):
    monkeypatch.setattr(
        providerless_canary.subprocess,
        "run",
        lambda *_args, **_kwargs: CompletedProcess([], 0, stdout="not-a-commit\n"),
    )
    with pytest.raises(RuntimeError, match="exact lowercase source commit"):
        providerless_canary.run_canary(tmp_path)
