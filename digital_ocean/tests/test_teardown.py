def test_teardown_rollback(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.teardown.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.droplets.list.return_value = {"droplets": [{"id": 12345, "name": "base2-app"}]}
        mock_client.droplets.delete.side_effect = Exception("Delete failed")
        test_args = ["teardown.py"]
        with mock.patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as e:
                teardown.main()
            assert e.value.code == 4
            captured = capsys.readouterr()
            assert "ROLLBACK ERROR" in captured.err
import os
import sys
import pytest
from unittest import mock
from digital_ocean import teardown

def test_teardown_env_missing(monkeypatch):
    monkeypatch.delenv("DO_API_TOKEN", raising=False)
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    with pytest.raises(SystemExit) as e:
        teardown.main()
    assert e.value.code == 1

def test_teardown_droplet_not_found(monkeypatch):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.teardown.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.droplets.list.return_value = {"droplets": []}
        test_args = ["teardown.py"]
        with mock.patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as e:
                teardown.main()
            assert e.value.code == 2

def test_teardown_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.teardown.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.droplets.list.return_value = {"droplets": [{"id": 12345, "name": "base2-app"}]}
        test_args = ["teardown.py", "--dry-run"]
        with mock.patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as e:
                teardown.main()
            assert e.value.code == 0
            out = capsys.readouterr().out
            assert "[DRY RUN]" in out

def test_teardown_delete(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.teardown.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.droplets.list.return_value = {"droplets": [{"id": 12345, "name": "base2-app"}]}
        test_args = ["teardown.py"]
        with mock.patch.object(sys, 'argv', test_args):
            teardown.main()
            out = capsys.readouterr().out
            assert "deleted" in out
            assert mock_client.droplets.delete.called

def test_teardown_api_error(monkeypatch):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.teardown.Client") as MockClient:
        MockClient.return_value.droplets.list.side_effect = Exception("API fail")
        test_args = ["teardown.py"]
        with mock.patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as e:
                teardown.main()
            assert e.value.code == 3