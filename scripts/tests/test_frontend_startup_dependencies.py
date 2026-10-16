"""Regression for the live frontend restart before API DNS existed (F114-14)."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("filename", ["local.docker.yml", "development.docker.yml"])
def test_frontend_waits_for_healthy_api_without_dependency_cycle(filename):
    services = yaml.safe_load((ROOT / filename).read_text())["services"]
    assert services["react-app"].get("depends_on", {}).get("api") == {
        "condition": "service_healthy"
    }
    assert services["api"]["healthcheck"]["test"]
    assert not services["api"]["healthcheck"].get("disable", False)

    def visit(name, ancestors):
        assert name not in ancestors, f"dependency cycle at {name}"
        for dependency in services[name].get("depends_on", {}):
            visit(dependency, ancestors | {name})

    visit("react-app", set())


def test_frontend_upstream_remains_fixed_and_internal():
    source = (ROOT / "react-app/nginx/default.conf").read_text()
    assert "proxy_pass http://api:5001;" in source
    assert "proxy_pass $" not in source
    assert "proxy_connect_timeout 5s;" in source
