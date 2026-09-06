from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import media_library
from api.security.request_auth import PublicPrincipal


ASSET_ID = "00000000-0000-0000-0000-000000000110"
app = FastAPI()
app.include_router(media_library.router, prefix="/api")


class Repository:
    def list_assets(self, **kwargs):
        assert kwargs["site_id"] == "base2-obsidian"
        return {"items": [], "nextOffset": None, "indexStatus": "current"}

    def get_asset(self, **kwargs):
        assert kwargs["site_id"] == "base2-obsidian"
        return {"id": str(kwargs["asset_id"]), "status": "ready"}

    def update_metadata(self, **kwargs):
        assert kwargs["expected_version"] == 2
        return {"id": str(kwargs["asset_id"]), "revision": 1, "version": 3}


@pytest.fixture(autouse=True)
def scoped(monkeypatch):
    principal = PublicPrincipal(UUID(int=110), datetime.now(UTC), True)
    monkeypatch.setattr(media_library, "require_authenticated_principal", lambda _request: principal)
    monkeypatch.setattr(media_library, "require_tenant", lambda _request: "base2-obsidian")
    monkeypatch.setattr(media_library, "authorize", lambda **_kwargs: {})
    monkeypatch.setattr(media_library, "get_repository", Repository)


def test_capabilities_are_closed_and_do_not_expose_storage_details():
    response = TestClient(app).get("/api/media/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["schemaVersion"] == 1
    assert all(set(item) == {"mediaType", "extensions", "delivery"} for item in body["formats"])
    assert "storage" not in str(body).lower()


def test_list_and_detail_are_scoped():
    client = TestClient(app)
    assert client.get("/api/media/v1/assets?state=ready&limit=25").status_code == 200
    assert client.get(f"/api/media/v1/assets/{ASSET_ID}").status_code == 200
    assert client.get("/api/media/v1/assets?state=unknown").status_code == 422
    assert client.get("/api/media/v1/assets?media_type=text/html").status_code == 422


def test_metadata_contract_rejects_unknown_fields_and_requires_version():
    client = TestClient(app)
    good = {
        "locale": "en", "altText": "A useful description", "decorative": False,
        "caption": "", "credit": "", "licenseCode": "", "visibility": "private",
    }
    assert client.put(f"/api/media/v1/assets/{ASSET_ID}/metadata", json=good).status_code == 422
    response = client.put(
        f"/api/media/v1/assets/{ASSET_ID}/metadata",
        json={**good, "unknown": True}, headers={"If-Match": '"2"'},
    )
    assert response.status_code == 422
    response = client.put(
        f"/api/media/v1/assets/{ASSET_ID}/metadata",
        json=good, headers={"If-Match": '"2"'},
    )
    assert response.status_code == 200 and response.json()["version"] == 3


def test_content_transfer_uses_header_grants_and_safe_delivery_headers(monkeypatch):
    monkeypatch.setattr(media_library, "get_artifact_store", lambda: object())
    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        "complete_asset_upload",
        lambda _self, **kwargs: {
            "id": str(kwargs["asset_id"]), "status": "quarantined", "sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        "read_asset_content",
        lambda _self, **_kwargs: {
            "content": b"safe-png", "media_type": "image/png", "sha256": "a" * 64,
        },
    )
    client = TestClient(app)
    response = client.put(
        f"/api/media/v1/assets/{ASSET_ID}/content",
        content=b"safe-png",
        headers={"Upload-Grant": "g" * 64, "Content-Type": "image/png"},
    )
    assert response.status_code == 200 and response.json()["status"] == "quarantined"
    response = client.get(
        f"/api/media/v1/assets/{ASSET_ID}/content",
        headers={"Download-Grant": "g" * 64},
    )
    assert response.status_code == 200 and response.content == b"safe-png"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == "default-src 'none'; sandbox"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize(
    "payload",
    [
        {"filename": "../../escape.png", "mediaType": "image/png", "byteSize": 1, "sha256": "a" * 64},
        {"filename": "active.svg", "mediaType": "image/png", "byteSize": 1, "sha256": "a" * 64},
        {"filename": "page.html", "mediaType": "text/html", "byteSize": 1, "sha256": "a" * 64},
    ],
)
def test_upload_contract_rejects_hostile_metadata_before_repository(monkeypatch, payload):
    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        "create_asset_upload",
        lambda *_args, **_kwargs: pytest.fail("repository must not be called"),
    )
    response = TestClient(app).post("/api/media/v1/uploads", json=payload)
    assert response.status_code == 422
