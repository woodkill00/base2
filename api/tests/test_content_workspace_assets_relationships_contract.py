from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import content_workspace
from api.security.request_auth import PublicPrincipal


class FakeRepository:
    calls: list[tuple[str, dict]] = []

    def create_asset_upload(self, **kwargs):
        self.calls.append(('upload', kwargs))
        return {'id': str(UUID(int=7104)), 'status': 'pending', 'uploadGrant': 'opaque'}

    def get_asset(self, **kwargs):
        self.calls.append(('asset', kwargs))
        return {'id': str(kwargs['asset_id']), 'status': 'validated', 'mediaType': 'image/png'}

    def complete_asset_upload(self, **kwargs):
        self.calls.append(('upload-content', kwargs))
        return {
            'id': str(kwargs['asset_id']),
            'status': 'quarantined',
            'sha256': 'a' * 64,
            'replayed': False,
        }

    def read_asset_content(self, **kwargs):
        self.calls.append(('asset-content', kwargs))
        return {'content': b'safe-png', 'media_type': 'image/png', 'sha256': 'b' * 64}

    def bind_asset(self, **kwargs):
        self.calls.append(('bind', kwargs))
        return {'id': str(UUID(int=8104)), 'recordVersion': kwargs['expected_version'] + 1}

    def unbind_asset(self, **kwargs):
        self.calls.append(('unbind', kwargs))
        return {'deleted': True, 'recordVersion': kwargs['expected_version'] + 1}

    def list_relationships(self, **kwargs):
        self.calls.append(('relationships', kwargs))
        return {'items': []}

    def create_relationship(self, **kwargs):
        self.calls.append(('relationship-create', kwargs))
        return {'id': str(UUID(int=9104)), 'recordVersion': kwargs['expected_version'] + 1}

    def delete_relationship(self, **kwargs):
        self.calls.append(('relationship-delete', kwargs))
        return {'deleted': True, 'recordVersion': kwargs['expected_version'] + 1}


@pytest.fixture(autouse=True)
def scoped(monkeypatch):
    FakeRepository.calls = []
    principal = PublicPrincipal(UUID(int=104), datetime.now(UTC), True)
    monkeypatch.setattr(
        content_workspace, 'require_authenticated_principal', lambda request: principal
    )
    monkeypatch.setattr(content_workspace, 'require_tenant', lambda request: 'site-a')
    monkeypatch.setattr(content_workspace, 'workspace_enabled', lambda: True)
    monkeypatch.setattr(content_workspace, 'authorize', lambda **kwargs: {'role': 'owner'})
    monkeypatch.setattr(content_workspace, 'get_repository', lambda: FakeRepository())
    monkeypatch.setattr(content_workspace, 'get_artifact_store', lambda: object())


def test_asset_admission_status_and_binding_are_scoped_and_versioned():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    admitted = client.post(
        '/api/content/v1/assets/uploads',
        headers=headers,
        json={
            'filename': 'safe.png',
            'mediaType': 'image/png',
            'byteSize': 32,
            'sha256': 'a' * 64,
        },
    )
    assert admitted.status_code == 201 and admitted.json()['status'] == 'pending'
    asset_id = admitted.json()['id']
    assert client.get(f'/api/content/v1/assets/{asset_id}', headers=headers).status_code == 200
    record_id = str(UUID(int=3104))
    bound = client.post(
        f'/api/content/v1/types/article/records/{record_id}/assets/hero',
        headers=headers,
        json={'assetId': asset_id, 'expectedVersion': 1, 'altText': 'Synthetic image'},
    )
    assert bound.status_code == 201 and bound.json()['recordVersion'] == 2
    assert (
        client.delete(
            f'/api/content/v1/types/article/records/{record_id}/assets/hero'
            f'?asset_id={asset_id}&expected_version=2',
            headers=headers,
        ).status_code
        == 200
    )
    assert all(call[1]['site_id'] == 'site-a' for call in FakeRepository.calls)


def test_asset_content_upload_is_raw_bounded_grant_bound_and_starts_quarantined():
    client = TestClient(app)
    headers = {
        'Authorization': 'Bearer synthetic',
        'X-Tenant-ID': 'site-a',
        'Upload-Grant': 'opaque-upload-grant-that-is-long-enough',
        'Content-Type': 'image/png',
    }
    asset_id = str(UUID(int=7104))
    response = client.put(
        f'/api/content/v1/assets/{asset_id}/content',
        headers=headers,
        content=b'synthetic raw body',
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'quarantined'
    call = next(item for item in FakeRepository.calls if item[0] == 'upload-content')
    assert call[1]['site_id'] == 'site-a'
    assert call[1]['content'] == b'synthetic raw body'
    assert call[1]['upload_grant'] == headers['Upload-Grant']


def test_asset_content_upload_rejects_oversize_before_repository(monkeypatch):
    monkeypatch.setattr(content_workspace, 'MAX_UPLOAD_BYTES', 4)
    client = TestClient(app)
    response = client.put(
        f'/api/content/v1/assets/{UUID(int=7104)}/content',
        headers={
            'Authorization': 'Bearer synthetic',
            'X-Tenant-ID': 'site-a',
            'Upload-Grant': 'opaque-upload-grant-that-is-long-enough',
        },
        content=b'12345',
    )
    assert response.status_code == 413
    assert response.json()['detail'] == 'content_limit_exceeded'
    assert not any(item[0] == 'upload-content' for item in FakeRepository.calls)


def test_asset_content_download_requires_header_grant_and_is_private_nosniff():
    client = TestClient(app)
    asset_id = str(UUID(int=7104))
    base_headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}

    assert (
        client.get(f'/api/content/v1/assets/{asset_id}/content', headers=base_headers).status_code
        == 422
    )
    headers = {**base_headers, 'Download-Grant': 'opaque-download-grant-that-is-long-enough'}
    response = client.get(f'/api/content/v1/assets/{asset_id}/content', headers=headers)

    assert response.status_code == 200 and response.content == b'safe-png'
    assert response.headers['content-type'] == 'image/png'
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    call = next(item for item in FakeRepository.calls if item[0] == 'asset-content')
    assert call[1]['site_id'] == 'site-a'
    assert call[1]['download_grant'] == headers['Download-Grant']


def test_relationship_lifecycle_is_bounded_and_never_accepts_scope_from_body():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    record_id = str(UUID(int=3104))
    target_id = str(UUID(int=3204))
    endpoint = f'/api/content/v1/types/article/records/{record_id}/relationships'
    assert client.get(endpoint, headers=headers).status_code == 200
    created = client.post(
        endpoint,
        headers=headers,
        json={
            'fieldKey': 'related',
            'targetId': target_id,
            'expectedVersion': 1,
            'deletionPolicy': 'restrict',
        },
    )
    assert created.status_code == 201 and created.json()['recordVersion'] == 2
    relationship_id = created.json()['id']
    assert (
        client.delete(
            f'{endpoint}/{relationship_id}?expected_version=2', headers=headers
        ).status_code
        == 200
    )
    unsafe = client.post(
        endpoint,
        headers=headers,
        json={
            'fieldKey': 'related',
            'targetId': target_id,
            'expectedVersion': 1,
            'siteId': 'site-b',
        },
    )
    assert unsafe.status_code == 422
