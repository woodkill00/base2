"""
pytest for exec script (digital_ocean/exec.py)
Validates argument parsing, error handling, and logging for exec operations.
"""
import os
import sys
import pytest
from unittest import mock

# Patch environment for tests
@mock.patch.dict(os.environ, {"DO_API_TOKEN": "test-token"})
def test_exec_droplet(monkeypatch, capsys):
    class MockClient:
        def __init__(self, token=None):
            pass
    monkeypatch.setattr("digital_ocean.exec.Client", MockClient)
    import digital_ocean.exec as exec_mod
    # Patch exec_on_droplet to check call
    called = {}
    def fake_exec_on_droplet(client, droplet_id, command):
        called["droplet_id"] = droplet_id
        called["command"] = command
        return 0
    monkeypatch.setattr(exec_mod, "exec_on_droplet", fake_exec_on_droplet)
    test_args = ["exec.py", "--droplet", "droplet-123", "--cmd", "ls -l"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit) as e:
        exec_mod.main()
    assert e.value.code == 0
    assert called["droplet_id"] == "droplet-123"
    assert called["command"] == "ls -l"

@mock.patch.dict(os.environ, {"DO_API_TOKEN": "test-token"})
def test_exec_app_missing_service(monkeypatch, capsys):
    import digital_ocean.exec as exec_mod
    test_args = ["exec.py", "--app", "app-123", "--cmd", "ls"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit) as e:
        exec_mod.main()
    assert e.value.code == 2
    captured = capsys.readouterr()
    assert "--service is required" in captured.err

@mock.patch.dict(os.environ, {})
def test_exec_missing_env(monkeypatch):
    import digital_ocean.exec as exec_mod
    test_args = ["exec.py", "--droplet", "droplet-123", "--cmd", "ls"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit) as e:
        exec_mod.main()
    assert e.value.code == 1
