"""
Pytest self-tests for env_check.py
Checks that missing required variables cause failure and all set variables pass.
"""

import pytest

from digital_ocean.scripts.python import env_check


@pytest.mark.parametrize("missing_var", env_check.REQUIRED_VARS)
def test_missing_env_var(monkeypatch, missing_var):
    # Unset all required vars, then set all except one
    for var in env_check.REQUIRED_VARS:
        monkeypatch.delenv(var, raising=False)
    for var in env_check.REQUIRED_VARS:
        if var != missing_var:
            monkeypatch.setenv(var, "dummy")
    # Should exit with error
    with pytest.raises(SystemExit) as e:
        env_check.check_required_env_vars()
    assert e.value.code == 1


def test_all_required_vars_set(monkeypatch):
    for var in env_check.REQUIRED_VARS:
        monkeypatch.setenv(var, "dummy")
    # Should not exit
    env_check.check_required_env_vars()


def test_preflight_loads_strict_normalized_file(monkeypatch, tmp_path, capsys):
    path = tmp_path / ".env"
    path.write_text(
        'DO_API_TOKEN="secret"\nDO_API_REGION = fra1\n'
        "DO_API_IMAGE=ubuntu-22-04-x64\nDO_APP_NAME=base2-preview\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_ENV_PATH", str(path))
    monkeypatch.setattr(env_check.sys, "argv", ["env_check.py"])
    env_check.main()
    assert "All required" in capsys.readouterr().out


def test_preflight_rejects_ambiguous_file_without_echoing_secret(monkeypatch, tmp_path, capsys):
    secret = "never-print-this"
    path = tmp_path / ".env"
    path.write_text(
        f"DO_API_TOKEN={secret}\nDO_API_TOKEN=second\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_ENV_PATH", str(path))
    monkeypatch.setattr(env_check.sys, "argv", ["env_check.py"])
    with pytest.raises(SystemExit) as error:
        env_check.main()
    captured = capsys.readouterr()
    assert error.value.code == 2
    assert "duplicate key DO_API_TOKEN" in captured.err
    assert secret not in captured.err


def test_orchestrator_uses_single_strict_parser():
    source = (
        env_check.Path(__file__).resolve().parents[1] / "scripts/python/orchestrate_deploy.py"
    ).read_text(encoding="utf-8")
    assert source.count("load_deploy_config(env_path)") == 1
    assert "dotenv_values" not in source
    assert "load_dotenv" not in source
