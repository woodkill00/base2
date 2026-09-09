import json
import sys
from types import SimpleNamespace

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
        self.tags = _Tags()


class _Tags:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.failure = None

    def create(self, **kwargs):
        if self.failure:
            raise self.failure
        self.created.append(kwargs)

    def delete(self, **kwargs):
        if self.failure:
            raise self.failure
        self.deleted.append(kwargs)


def droplet(name="site-droplet", ips=("203.0.113.10",)):
    return {
        "id": 42,
        "name": name,
        "networks": {"v4": [{"type": "public", "ip_address": value} for value in ips]},
    }


def test_paginates_and_returns_one_authoritative_match():
    client = _Client([[droplet("other")], [droplet()], []])
    result = droplet_lookup.lookup(client, "site-droplet", page_size=1)
    assert result == {"state": "found", "id": "42", "ip": "203.0.113.10"}
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
    with pytest.raises(ValueError, match="empty_droplet_name"):
        droplet_lookup.resolve_name("   ", "site")


@pytest.mark.parametrize("invalid_id", (None, "42", 0, -1))
def test_found_droplet_requires_positive_integer_provider_identity(invalid_id):
    item = droplet()
    item["id"] = invalid_id
    with pytest.raises(RuntimeError, match="invalid_provider_identity"):
        droplet_lookup.lookup(_Client([[item]]), "site-droplet")


def test_main_reports_safe_error_without_token(monkeypatch, capsys):
    monkeypatch.delenv("DO_API_TOKEN", raising=False)
    assert droplet_lookup.main() == 2
    assert json.loads(capsys.readouterr().out) == {"state": "error", "id": "", "ip": ""}


def test_main_emits_typed_success_from_injected_provider(monkeypatch, capsys):
    client = _Client([[droplet()]])
    monkeypatch.setenv("DO_API_TOKEN", "fixture-token")
    monkeypatch.setenv("PROJECT_NAME", "site")
    monkeypatch.setenv("DO_DROPLET_NAME", "${PROJECT_NAME}-droplet")
    monkeypatch.setitem(sys.modules, "pydo", SimpleNamespace(Client=lambda token: client))
    assert droplet_lookup.main() == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "found",
        "id": "42",
        "ip": "203.0.113.10",
    }


def test_main_fails_closed_on_provider_error(monkeypatch, capsys):
    monkeypatch.setenv("DO_API_TOKEN", "fixture-token")
    monkeypatch.setitem(
        sys.modules,
        "pydo",
        SimpleNamespace(Client=lambda token: (_ for _ in ()).throw(OSError("offline"))),
    )
    assert droplet_lookup.main() == 3
    assert json.loads(capsys.readouterr().out) == {"state": "error", "id": "", "ip": ""}


def test_provider_lease_is_atomic_and_fail_closed():
    client = _Client([[]])
    droplet_lookup.acquire_provider_lease(client, "base2-provision-lease")
    droplet_lookup.release_provider_lease(client, "base2-provision-lease")
    assert client.tags.created == [{"body": {"name": "base2-provision-lease"}}]
    assert client.tags.deleted == [{"tag_id": "base2-provision-lease"}]
    client.tags.failure = OSError("provider details must remain hidden")
    with pytest.raises(RuntimeError, match="lease_unavailable"):
        droplet_lookup.acquire_provider_lease(client, "base2-provision-lease")
    with pytest.raises(RuntimeError, match="lease_release_failed"):
        droplet_lookup.release_provider_lease(client, "base2-provision-lease")
