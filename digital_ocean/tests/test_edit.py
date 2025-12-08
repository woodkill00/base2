import os
import sys
import pytest
from unittest import mock
from digital_ocean import edit

def test_edit_env_missing(monkeypatch):
    monkeypatch.delenv("DO_API_TOKEN", raising=False)
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with pytest.raises(SystemExit) as e:
        edit.main()
    assert e.value.code == 1

def test_edit_droplet_not_found(monkeypatch):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.edit.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.droplets.list.return_value = {"droplets": []}
        with pytest.raises(SystemExit) as e:
            edit.main()
        assert e.value.code == 2

def test_edit_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.edit.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.droplets.list.return_value = {"droplets": [{"id": 12345, "name": "base2-app"}]}
        test_args = ["edit.py", "--dry-run"]
        with mock.patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as e:
                edit.main()
            assert e.value.code == 0
            out = capsys.readouterr().out
            assert "[DRY RUN]" in out

def test_edit_update(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.edit.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.droplets.list.return_value = {"droplets": [{"id": 12345, "name": "base2-app"}]}
        mock_client.tags.create.return_value = None
        mock_client.tags.tag_resource.return_value = None
        test_args = ["edit.py"]
        with mock.patch.object(sys, 'argv', test_args):
            edit.main()
            out = capsys.readouterr().out
            assert "updated" in out
            assert mock_client.tags.create.called
            assert mock_client.tags.tag_resource.called

def test_edit_api_error(monkeypatch):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.edit.Client") as MockClient:
        MockClient.return_value.droplets.list.side_effect = Exception("API fail")
        with pytest.raises(SystemExit) as e:
            edit.main()
        assert e.value.code == 3

def test_edit_rollback(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    with mock.patch("digital_ocean.edit.Client") as MockClient:
        mock_client = MockClient.return_value
        mock_client.droplets.list.return_value = {"droplets": [{"id": 12345, "name": "base2-app"}]}
        mock_client.tags.create.side_effect = Exception("Update failed")
        test_args = ["edit.py"]
        with mock.patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as e:
                edit.main()
            assert e.value.code == 4
            captured = capsys.readouterr()
            assert "ROLLBACK ERROR" in captured.err