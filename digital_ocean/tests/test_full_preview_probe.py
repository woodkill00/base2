from types import SimpleNamespace

import pytest

from digital_ocean.scripts.python import full_preview_probe
from digital_ocean.scripts.python.full_preview_probe import ProbeError, Response, safe_json, verify_full_preview


def transport(host, path, ip, authorization):
    protected = host != "woodkilldev.com"
    status = 401 if protected and authorization is None else 200
    return Response(status, {"x-robots-tag": "noindex"}, b"fixture")


def test_route_matrix_checks_public_anonymous_and_protected_authorized():
    result = verify_full_preview(
        "woodkilldev.com", "203.0.113.8", username="owner", password="safe-secret",
        owner_cidrs=["8.8.8.8/32"], transport=transport,
    )
    assert result["ok"] and result["routeCount"] == 8
    assert result["credentialsReturned"] is False
    assert "safe-secret" not in safe_json(result)


def test_anonymous_operator_success_fails_closed():
    def open_transport(host, path, ip, authorization):
        return Response(200, {}, b"")
    try:
        verify_full_preview(
            "woodkilldev.com", "203.0.113.8", username="owner", password="secret",
            owner_cidrs=["8.8.8.8/32"], transport=open_transport,
        )
    except ProbeError as error:
        assert "anonymously reachable" in str(error)
    else:
        raise AssertionError("unguarded operator route was accepted")


def test_credentials_reject_control_characters():
    try:
        verify_full_preview(
            "woodkilldev.com", "203.0.113.8", username="owner", password="bad\nvalue",
            owner_cidrs=["8.8.8.8/32"], transport=transport,
        )
    except ProbeError as error:
        assert "credentials" in str(error)
    else:
        raise AssertionError("hostile credentials were accepted")


def test_default_https_transport_is_bounded_and_closes(monkeypatch):
    class Reply:
        status = 200

        def read(self, limit):
            assert limit == 262_145
            return b"healthy"

        def getheaders(self):
            return [("X-Robots-Tag", "noindex")]

    class Connection:
        def __init__(self, *args, **kwargs):
            self.closed = False

        def request(self, method, path, headers):
            assert method == "GET" and headers["Host"] == "woodkilldev.com"

        def getresponse(self):
            return Reply()

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(full_preview_probe.http.client, "HTTPSConnection", lambda *a, **k: connection)
    result = full_preview_probe._request(
        "woodkilldev.com", "/api/health", "8.8.8.8", "Basic safe"
    )
    assert result == Response(200, {"x-robots-tag": "noindex"}, b"healthy")
    assert connection.closed is True


def test_default_transport_rejects_oversized_response(monkeypatch):
    reply = SimpleNamespace(
        status=200,
        read=lambda limit: b"x" * 262_145,
        getheaders=lambda: [],
    )
    connection = SimpleNamespace(
        request=lambda *a, **k: None,
        getresponse=lambda: reply,
        close=lambda: None,
    )
    monkeypatch.setattr(full_preview_probe.http.client, "HTTPSConnection", lambda *a, **k: connection)
    with pytest.raises(ProbeError, match="safe bound"):
        full_preview_probe._request("woodkilldev.com", "/", "8.8.8.8", None)


@pytest.mark.parametrize(
    "domain,address,message",
    [("unsafe", "8.8.8.8", "domain"), ("woodkilldev.com", "not-an-ip", "IP")],
)
def test_probe_rejects_invalid_endpoint_identity(domain, address, message):
    with pytest.raises(ProbeError, match=message):
        verify_full_preview(
            domain,
            address,
            username="owner",
            password="secret",
            owner_cidrs=["8.8.4.4/32"],
            transport=transport,
        )


def test_public_and_authorized_failures_are_explicit():
    with pytest.raises(ProbeError, match="public route"):
        verify_full_preview(
            "woodkilldev.com",
            "8.8.8.8",
            username="owner",
            password="secret",
            owner_cidrs=["8.8.4.4/32"],
            transport=lambda *args: Response(500, {}, b""),
        )

    def denied(host, path, ip, authorization):
        if host == "woodkilldev.com":
            return Response(200, {}, b"")
        return Response(401 if authorization is None else 500, {}, b"")

    with pytest.raises(ProbeError, match="authorized route"):
        verify_full_preview(
            "woodkilldev.com",
            "8.8.8.8",
            username="owner",
            password="secret",
            owner_cidrs=["8.8.4.4/32"],
            transport=denied,
        )
