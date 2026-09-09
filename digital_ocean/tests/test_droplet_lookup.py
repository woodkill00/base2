import json

import pytest

from digital_ocean.scripts.python import droplet_lookup


class _Droplets:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        value = self.pages[kwargs["page"] - 1]
        if isinstance(value, Exception):
            raise value
        return {"droplets": value}


class _Client:
    def __init__(self, pages):
        self.droplets = _Droplets(pages)


def droplet(name="site-droplet", ips=("203.0.113.10",)):
    return {
        "name": name,
        "networks": {"v4": [{"type": "public", "ip_address": value} for value in ips]},
    }


def test_paginates_and_returns_one_authoritative_match():
    client = _Client([[droplet("other")], [droplet()], []])
    result = droplet_lookup.lookup(client, "site-droplet", page_size=1)
    assert result == {"state": "found", "ip": "203.0.113.10"}
    assert client.droplets.calls == [
        {"page": 1, "per_page": 1},
        {"page": 2, "per_page": 1},
        {"page": 3, "per_page": 1},
    ]


@pytest.mark.parametrize(
    ("pages", "state"),
    [
        ([[]], "missing"),
        ([[droplet(ips=())]], "pending"),
        ([[droplet(), droplet()]], "ambiguous"),
        ([[droplet(ips=("203.0.113.10", "203.0.113.11"))]], "ambiguous"),
    ],
)
def test_never_collapses_pending_or_ambiguous_into_missing(pages, state):
    assert droplet_lookup.lookup(_Client(pages), "site-droplet")["state"] == state


def test_rejects_provider_errors_and_malformed_responses():
    with pytest.raises(OSError):
        droplet_lookup.lookup(_Client([OSError("offline")]), "site-droplet")
    client = _Client([[]])
    client.droplets.list = lambda **_kwargs: {"droplets": None}
    with pytest.raises(RuntimeError, match="invalid_provider_response"):
        droplet_lookup.lookup(client, "site-droplet")


def test_name_resolution_is_bounded():
    assert droplet_lookup.resolve_name("${PROJECT_NAME}-droplet", "site") == "site-droplet"
    with pytest.raises(ValueError, match="invalid_droplet_name_template"):
        droplet_lookup.resolve_name("${UNKNOWN}-droplet", "site")


def test_main_reports_safe_error_without_token(monkeypatch, capsys):
    monkeypatch.delenv("DO_API_TOKEN", raising=False)
    assert droplet_lookup.main() == 2
    assert json.loads(capsys.readouterr().out) == {"state": "error", "ip": ""}
