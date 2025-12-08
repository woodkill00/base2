
import os
import sys
import pytest
from unittest import mock
from digital_ocean import deploy

def test_deploy_env_missing(monkeypatch):
    monkeypatch.delenv("DO_API_TOKEN", raising=False)
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    with pytest.raises(SystemExit) as e:
        deploy.main()
    assert e.value.code == 1

def test_deploy_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    test_args = ["deploy.py", "--dry-run"]
    with mock.patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            deploy.main()
        assert e.value.code == 0
        out = capsys.readouterr().out
        assert "[DRY RUN]" in out

def test_deploy_api_error(monkeypatch):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    # Patch Client to raise error
    with mock.patch("digital_ocean.deploy.Client") as MockClient:
        MockClient.return_value.droplets.create.side_effect = Exception("API fail")
        test_args = ["deploy.py"]
        with mock.patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as e:
                deploy.main()
            assert e.value.code == 2

def test_deploy_rollback(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "dummy")
    monkeypatch.setenv("DO_API_REGION", "nyc3")
    monkeypatch.setenv("DO_API_IMAGE", "docker-20-04")
    monkeypatch.setenv("DO_APP_NAME", "base2-app")
    # Simulate droplet creation succeeds, but error occurs in post-creation step
    with mock.patch("digital_ocean.deploy.Client") as MockClient:
        mock_client = MockClient.return_value
        # Simulate droplet creation returns a droplet with id
        mock_client.droplets.create.return_value = {"droplet": {"id": 12345}}
        # Patch post_creation_hook to raise exception
        with mock.patch("digital_ocean.deploy.post_creation_hook", side_effect=Exception("Simulated failure after droplet creation")):
            test_args = ["deploy.py"]
            with mock.patch.object(sys, 'argv', test_args):
                with pytest.raises(SystemExit) as e:
                    deploy.main()
                # Should attempt rollback (delete)
                assert mock_client.droplets.delete.called