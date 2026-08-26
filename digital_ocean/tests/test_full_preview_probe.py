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
