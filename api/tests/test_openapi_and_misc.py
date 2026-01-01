from fastapi.testclient import TestClient

# Import the FastAPI app
from api.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_openapi_includes_security_schemes():
    # Ensure our custom OpenAPI generator adds required security schemes
    schema = app.openapi()
    comps = schema.get("components", {})
    sec = comps.get("securitySchemes", {})
    assert "SessionCookie" in sec
    assert "CsrfToken" in sec
    assert sec["SessionCookie"].get("in") == "cookie"
    assert sec["CsrfToken"].get("in") == "header"


def test_flags_endpoint_returns_dict():
    c = _client()
    r = c.get("/flags")
    assert r.status_code == 200
    j = r.json()
    assert isinstance(j, dict)
    assert "flags" in j


def test_metrics_endpoint_exposes_prometheus_text():
    c = _client()
    r = c.get("/metrics")
    assert r.status_code == 200
    # Play nice with content-type variations from FastAPI/Starlette
    ct = r.headers.get("content-type", "")
    assert ct.startswith("text/plain")
    body = r.text
    assert "# TYPE base2_api_requests_total counter" in body
    assert "base2_api_uptime_seconds" in body


def test_privacy_endpoints_require_tenant_header_and_succeed():
    c = _client()
    # Missing header should fail
    r_missing = c.post("/privacy/export")
    assert r_missing.status_code == 400
    assert r_missing.json().get("detail") == "tenant_required"

    # With header, operations should be accepted
    hdr = {"X-Tenant-Id": "t-123"}
    r_export = c.post("/privacy/export", headers=hdr)
    assert r_export.status_code == 200
    j_export = r_export.json()
    assert j_export.get("accepted") is True
    assert j_export.get("operation") == "export"
    assert j_export.get("tenant_id") == "t-123"

    r_delete = c.post("/privacy/delete", headers=hdr)
    assert r_delete.status_code == 200
    j_delete = r_delete.json()
    assert j_delete.get("accepted") is True
    assert j_delete.get("operation") == "delete"
    assert j_delete.get("tenant_id") == "t-123"
