from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import content_workspace
from api.security.request_auth import PublicPrincipal


RECORD_ID = "00000000-0000-0000-0000-000000003104"
VIEW_ID = "00000000-0000-0000-0000-000000004104"
JOB_ID = "00000000-0000-0000-0000-000000005104"
ASSET_ID = "00000000-0000-0000-0000-000000007104"
RELATIONSHIP_ID = "00000000-0000-0000-0000-000000008104"
GRANT = "g" * 64
HEADERS = {
    "Authorization": "Bearer synthetic",
    "X-Tenant-ID": "site-a",
    "If-Match": '"1"',
    "Idempotency-Key": "bounded-replay-104",
    "Upload-Grant": GRANT,
    "Download-Grant": GRANT,
}


class RaisingRepository:
    def __init__(self, error: Exception):
        self.error = error

    def __getattr__(self, _name):
        def raise_closed(**_kwargs):
            raise self.error

        return raise_closed


REQUESTS = [
    ("get", "/api/content/v1/types", {}),
    (
        "post",
        "/api/content/v1/types",
        {"json": {"typeKey": "article", "name": "Article", "fields": []}},
    ),
    ("get", "/api/content/v1/types/article/versions/1", {}),
    ("post", "/api/content/v1/types/article/versions/1/preview", {}),
    (
        "post",
        "/api/content/v1/types/article/versions/1/publish",
        {"json": {"expectedLockVersion": 1, "confirmLossy": False}},
    ),
    (
        "post",
        "/api/content/v1/types/article/versions/1/retire",
        {"json": {"expectedLockVersion": 1}},
    ),
    ("get", "/api/content/v1/types/article/records", {}),
    ("get", "/api/content/v1/types/article/search?q=safe", {}),
    (
        "post",
        "/api/content/v1/types/article/records",
        {"json": {"slug": "safe", "title": "Safe", "values": {}}},
    ),
    (
        "patch",
        f"/api/content/v1/types/article/records/{RECORD_ID}",
        {"json": {"values": {}}},
    ),
    (
        "post",
        f"/api/content/v1/types/article/records/{RECORD_ID}/transitions/submit_review",
        {"json": {"expectedVersion": 1}},
    ),
    ("delete", f"/api/content/v1/types/article/records/{RECORD_ID}?expected_version=1", {}),
    ("get", f"/api/content/v1/types/article/records/{RECORD_ID}", {}),
    ("get", f"/api/content/v1/types/article/records/{RECORD_ID}/versions", {}),
    (
        "post",
        f"/api/content/v1/types/article/records/{RECORD_ID}/versions/1/restore",
        {"json": {"expectedVersion": 1}},
    ),
    ("get", "/api/content/v1/types/article/views", {}),
    (
        "post",
        "/api/content/v1/types/article/views",
        {
            "json": {
                "title": "Safe view",
                "query": {"filters": [], "sort": ["slug"], "fields": [], "expand": []},
            }
        },
    ),
    ("get", f"/api/content/v1/types/article/views/{VIEW_ID}", {}),
    (
        "patch",
        f"/api/content/v1/types/article/views/{VIEW_ID}",
        {"json": {"title": "Changed"}},
    ),
    ("delete", f"/api/content/v1/types/article/views/{VIEW_ID}?expected_version=1", {}),
    ("post", f"/api/content/v1/types/article/views/{VIEW_ID}/execute", {}),
    (
        "post",
        "/api/content/v1/assets/uploads",
        {
            "json": {
                "filename": "safe.png",
                "mediaType": "image/png",
                "byteSize": 8,
                "sha256": "a" * 64,
            }
        },
    ),
    ("get", f"/api/content/v1/assets/{ASSET_ID}", {}),
    (
        "put",
        f"/api/content/v1/assets/{ASSET_ID}/content",
        {"content": b"safe-png", "headers": {"Content-Type": "image/png"}},
    ),
    ("get", f"/api/content/v1/assets/{ASSET_ID}/content", {}),
    (
        "post",
        f"/api/content/v1/types/article/records/{RECORD_ID}/assets/cover_image",
        {"json": {"assetId": ASSET_ID, "expectedVersion": 1, "altText": "Safe"}},
    ),
    (
        "delete",
        f"/api/content/v1/types/article/records/{RECORD_ID}/assets/cover_image"
        f"?asset_id={ASSET_ID}&expected_version=1",
        {},
    ),
    ("get", f"/api/content/v1/types/article/records/{RECORD_ID}/relationships", {}),
    (
        "post",
        f"/api/content/v1/types/article/records/{RECORD_ID}/relationships",
        {
            "json": {
                "fieldKey": "related_items",
                "targetId": RECORD_ID,
                "expectedVersion": 1,
            }
        },
    ),
    (
        "delete",
        f"/api/content/v1/types/article/records/{RECORD_ID}/relationships/{RELATIONSHIP_ID}"
        "?expected_version=1",
        {},
    ),
    (
        "post",
        "/api/content/v1/types/article/imports",
        {
            "json": {
                "format": "json",
                "sourceSha256": "b" * 64,
                "schemaVersion": 1,
            }
        },
    ),
    ("get", f"/api/content/v1/types/article/imports/{JOB_ID}", {}),
    (
        "put",
        f"/api/content/v1/types/article/imports/{JOB_ID}/source",
        {"content": b"[]", "headers": {"Content-Type": "application/json"}},
    ),
    ("post", f"/api/content/v1/types/article/imports/{JOB_ID}/commit", {}),
    (
        "post",
        f"/api/content/v1/types/article/imports/{JOB_ID}/review",
        {"json": {"decisions": [{"ordinal": 1, "action": "skip"}]}},
    ),
    ("get", f"/api/content/v1/types/article/imports/{JOB_ID}/rows", {}),
    ("post", f"/api/content/v1/types/article/imports/{JOB_ID}/cancel", {}),
    (
        "post",
        "/api/content/v1/types/article/exports",
        {"json": {"format": "json", "schemaVersion": 1, "fields": []}},
    ),
    ("get", f"/api/content/v1/types/article/exports/{JOB_ID}", {}),
    ("post", f"/api/content/v1/types/article/exports/{JOB_ID}/download", {}),
    ("get", f"/api/content/v1/types/article/exports/{JOB_ID}/content", {}),
]


@pytest.fixture(autouse=True)
def scoped(monkeypatch):
    principal = PublicPrincipal(UUID(int=104), datetime.now(UTC), True)
    monkeypatch.setattr(
        content_workspace, "require_authenticated_principal", lambda request: principal
    )
    monkeypatch.setattr(content_workspace, "require_tenant", lambda request: "site-a")
    monkeypatch.setattr(content_workspace, "workspace_enabled", lambda: True)
    monkeypatch.setattr(content_workspace, "authorize", lambda **kwargs: None)
    monkeypatch.setattr(content_workspace, "get_artifact_store", lambda: object())


@pytest.mark.parametrize(("method", "url", "options"), REQUESTS)
@pytest.mark.parametrize(
    ("error", "expected"),
    [(ValueError("content_invalid"), {400, 404, 409, 422}), (RuntimeError("private"), {503})],
)
def test_route_failures_are_closed_redacted_and_non_successful(
    monkeypatch, method, url, options, error, expected
):
    monkeypatch.setattr(
        content_workspace, "get_repository", lambda: RaisingRepository(error)
    )
    request_options = dict(options)
    request_options["headers"] = {**HEADERS, **request_options.get("headers", {})}
    response = TestClient(app).request(method, url, **request_options)
    assert response.status_code in expected
    body = response.json()
    code = body["error"]["code"]
    assert isinstance(code, str) and code.startswith("content_")
    assert 8 <= len(code) <= 64
    assert "private" not in str(body)
