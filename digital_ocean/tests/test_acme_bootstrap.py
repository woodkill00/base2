from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from digital_ocean.scripts.python import bootstrap_acme as bootstrap_module
from digital_ocean.scripts.python.bootstrap_acme import (
    AcmeBootstrapError,
    bootstrap_acme,
    main,
    ownership_change_required,
)


def test_absent_storage_is_created_with_exact_contract(tmp_path):
    target = tmp_path / "letsencrypt"
    result = bootstrap_acme(target, uid=os.getuid(), gid=os.getgid())
    assert result["status"] == "ready"
    assert result["changed"] is True
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    for name in ("acme.json", "acme-staging.json"):
        path = target / name
        assert path.is_file()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_new_files_are_always_passed_through_identity_contract(tmp_path, monkeypatch):
    original = bootstrap_module._set_contract
    calls = []

    def observed(path, **kwargs):
        calls.append(Path(path).name)
        return original(path, **kwargs)

    monkeypatch.setattr(bootstrap_module, "_set_contract", observed)
    bootstrap_acme(tmp_path / "letsencrypt", uid=os.getuid(), gid=os.getgid())
    assert calls == ["letsencrypt", "acme.json", "acme-staging.json"]


def test_directory_path_that_is_a_file_fails_closed(tmp_path):
    target = tmp_path / "letsencrypt"
    target.write_text("not a directory", encoding="utf-8")
    with pytest.raises(AcmeBootstrapError, match="not a directory"):
        bootstrap_acme(target, uid=os.getuid(), gid=os.getgid())


def test_storage_file_that_is_a_directory_fails_closed(tmp_path):
    target = tmp_path / "letsencrypt"
    (target / "acme.json").mkdir(parents=True)
    with pytest.raises(AcmeBootstrapError, match="not a regular file"):
        bootstrap_acme(target, uid=os.getuid(), gid=os.getgid())


def test_symlink_storage_file_fails_closed(tmp_path):
    target = tmp_path / "letsencrypt"
    target.mkdir()
    (target / "real.json").write_text("", encoding="utf-8")
    (target / "acme.json").symlink_to(target / "real.json")
    with pytest.raises(AcmeBootstrapError, match="symlink"):
        bootstrap_acme(target, uid=os.getuid(), gid=os.getgid())


def test_wrong_modes_are_corrected_without_replacing_content(tmp_path):
    target = tmp_path / "letsencrypt"
    target.mkdir(mode=0o755)
    acme = target / "acme.json"
    acme.write_text('{"Account": "preserved"}', encoding="utf-8")
    acme.chmod(0o644)
    result = bootstrap_acme(target, uid=os.getuid(), gid=os.getgid())
    assert result["changed"] is True
    assert acme.read_text(encoding="utf-8") == '{"Account": "preserved"}'
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert stat.S_IMODE(acme.stat().st_mode) == 0o600


def test_wrong_owner_is_detected_from_metadata():
    metadata = type("Metadata", (), {"st_uid": 1001, "st_gid": 1002})()
    assert ownership_change_required(metadata, uid=1000, gid=1000) is True
    assert ownership_change_required(metadata, uid=1001, gid=1002) is False


def test_second_bootstrap_is_idempotent(tmp_path):
    target = tmp_path / "letsencrypt"
    first = bootstrap_acme(target, uid=os.getuid(), gid=os.getgid())
    second = bootstrap_acme(target, uid=os.getuid(), gid=os.getgid())
    assert first["changed"] is True
    assert second["changed"] is False
    assert first["files"] == second["files"]


def test_bash_wrapper_routes_to_the_single_python_implementation(tmp_path):
    root = Path(__file__).resolve().parents[2]
    target = tmp_path / "wrapper-letsencrypt"
    result = subprocess.run(
        [
            "bash",
            str(root / "scripts/bash/bootstrap-acme.sh"),
            "--directory",
            str(target),
            "--uid",
            str(os.getuid()),
            "--gid",
            str(os.getgid()),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ACME bootstrap: READY" in result.stdout


def test_powershell_wrapper_has_no_filesystem_implementation():
    root = Path(__file__).resolve().parents[2]
    wrapper = (root / "scripts/powershell/bootstrap-acme.ps1").read_text(encoding="utf-8")
    assert "bootstrap_acme.py" in wrapper
    assert "New-Item" not in wrapper
    assert "Set-Acl" not in wrapper


def test_cli_writes_receipt_and_reports_ready(tmp_path, monkeypatch, capsys):
    target = tmp_path / "cli-acme"
    output = tmp_path / "receipt.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bootstrap_acme.py",
            "--directory",
            str(target),
            "--uid",
            str(os.getuid()),
            "--gid",
            str(os.getgid()),
            "--output",
            str(output),
        ],
    )
    assert main() == 0
    assert '"status": "ready"' in output.read_text(encoding="utf-8")
    assert "READY" in capsys.readouterr().out


def test_cli_reports_typed_failure_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["bootstrap_acme.py", "--directory", str(tmp_path / "bad"), "--uid", "-1"],
    )
    assert main() == 1
    assert "FAILED" in capsys.readouterr().out


def test_directory_symlink_and_negative_identity_fail(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(AcmeBootstrapError, match="symlink"):
        bootstrap_acme(link, uid=os.getuid(), gid=os.getgid())
    with pytest.raises(AcmeBootstrapError, match="non-negative"):
        bootstrap_acme(tmp_path / "negative", uid=-1, gid=0)
