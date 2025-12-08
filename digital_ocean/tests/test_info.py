"""
pytest for info/query script (digital_ocean/info.py)
Validates listing of namespaces, domains, and resource metadata.
"""
import os
import sys
import pytest
from unittest import mock

# Patch environment for tests
@mock.patch.dict(os.environ, {"DO_API_TOKEN": "test-token"})
def test_info_lists(monkeypatch):
    # Mock PyDo Client and its methods
    class MockClient:
        def __init__(self, token=None):
            pass
        class projects:
            @staticmethod
            def list():
                return {"projects": [{"name": "proj1"}, {"name": "proj2"}]}
        class domains:
            @staticmethod
            def list():
                return {"domains": [{"name": "domain1.com"}, {"name": "domain2.com"}]}
        class droplets:
            @staticmethod
            def list():
                return {"droplets": [{"name": "droplet1"}]}
        class apps:
            @staticmethod
            def list():
                return {"apps": [{"spec": {"name": "app1"}}]}
        class volumes:
            @staticmethod
            def list():
                return {"volumes": [{"name": "vol1"}]}
    monkeypatch.setattr("digital_ocean.info.Client", MockClient)
    import digital_ocean.info as info
    client = info.get_client()
    assert info.list_namespaces(client) == ["proj1", "proj2"]
    assert info.list_domains(client) == ["domain1.com", "domain2.com"]
    resources = info.list_resource_metadata(client)
    assert resources["droplets"] == ["droplet1"]
    assert resources["apps"] == ["app1"]
    assert resources["volumes"] == ["vol1"]

# Error handling test
@mock.patch.dict(os.environ, {})
def test_info_missing_env():
    import importlib
    info = importlib.import_module("digital_ocean.info")
    with pytest.raises(SystemExit):
        info.validate_env()
