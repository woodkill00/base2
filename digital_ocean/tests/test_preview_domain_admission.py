import pytest

from digital_ocean.scripts.python.preview_lease_v2 import LeaseV2Conflict
from digital_ocean.tests.test_preview_startup_recovery import Client, Remote, invoke


def test_distinct_roots_same_domain_cannot_launch_concurrently(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()

    class DuringLaunch(Remote):
        def deploy(self, address, config):
            with pytest.raises(LeaseV2Conflict, match="operation busy"):
                invoke(second, object(), Remote())

    invoke(first, Client(), DuringLaunch())


def test_existing_other_preview_blocks_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    client = Client()
    client.droplets.list = lambda tag_name: {
        "droplets": [{"id": 777}] if tag_name == "base2-full-preview" else []
    }
    with pytest.raises(RuntimeError, match="another full preview"):
        invoke(tmp_path, client, Remote())
    assert client.droplets.row is None and client.droplets.deleted == []
