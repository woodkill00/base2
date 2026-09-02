from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import content_workspace
from api.security.request_auth import PublicPrincipal


class FakeJobRepository:
    calls: list[tuple[str, dict]] = []

    def create_import(self, **kwargs):
        self.calls.append(('import-create', kwargs))
        return {
            'id': str(UUID(int=5104)),
            'status': 'uploaded',
            'sourceReady': False,
            'uploadGrant': 'opaque-upload-grant-that-is-long-enough',
            'replayed': False,
        }

    def complete_import_source(self, **kwargs):
        self.calls.append(('import-source', kwargs))
        return {
            'id': str(kwargs['job_id']),
            'status': 'uploaded',
            'sourceReady': True,
            'replayed': False,
        }

    def get_import(self, **kwargs):
        self.calls.append(('import-get', kwargs))
        return {'id': str(kwargs['job_id']), 'status': 'validated', 'counters': {'valid': 2}}

    def commit_import(self, **kwargs):
        self.calls.append(('import-commit', kwargs))
        return {'id': str(kwargs['job_id']), 'status': 'completed', 'replayed': False}

    def cancel_import(self, **kwargs):
        self.calls.append(('import-cancel', kwargs))
        return {'id': str(kwargs['job_id']), 'status': 'cancelled'}

    def create_export(self, **kwargs):
        self.calls.append(('export-create', kwargs))
        return {'id': str(UUID(int=6104)), 'status': 'queued', 'replayed': False}

    def get_export(self, **kwargs):
        self.calls.append(('export-get', kwargs))
        return {'id': str(kwargs['job_id']), 'status': 'completed', 'outputSha256': 'a' * 64}

    def create_export_download(self, **kwargs):
        self.calls.append(('export-download', kwargs))
        return {'grant': 'opaque-synthetic-grant', 'expiresIn': 60}

    def read_export_content(self, **kwargs):
        self.calls.append(('export-content', kwargs))
        return {'content': b'title\nSynthetic\n', 'format': 'csv', 'sha256': 'a' * 64}


@pytest.fixture(autouse=True)
def scoped(monkeypatch):
    FakeJobRepository.calls = []
    principal = PublicPrincipal(UUID(int=104), datetime.now(UTC), True)
    monkeypatch.setattr(
        content_workspace, 'require_authenticated_principal', lambda request: principal
    )
    monkeypatch.setattr(content_workspace, 'require_tenant', lambda request: 'site-a')
    monkeypatch.setattr(content_workspace, 'workspace_enabled', lambda: True)
    monkeypatch.setattr(
        content_workspace,
        'authorize',
        lambda **kwargs: {'role': 'owner'},
    )
    monkeypatch.setattr(content_workspace, 'get_repository', lambda: FakeJobRepository())
    monkeypatch.setattr(content_workspace, 'get_artifact_store', lambda: object())


def test_import_and_export_lifecycle_is_tenant_principal_and_idempotency_bound():
    client = TestClient(app)
    headers = {
        'Authorization': 'Bearer synthetic',
        'X-Tenant-ID': 'site-a',
        'Idempotency-Key': 'synthetic-request-104',
    }
    imported = client.post(
        '/api/content/v1/types/article/imports',
        headers=headers,
        json={
            'format': 'json',
            'sourceSha256': 'b' * 64,
            'schemaVersion': 1,
            'mapping': {'Title': 'title'},
            'duplicatePolicy': 'review',
            'atomicPolicy': 'all_or_nothing',
        },
    )
    assert imported.status_code == 201 and imported.json()['status'] == 'uploaded'
    import_id = imported.json()['id']
    source = client.put(
        f'/api/content/v1/types/article/imports/{import_id}/source',
        headers={
            **headers,
            'Upload-Grant': imported.json()['uploadGrant'],
            'Content-Type': 'application/json',
        },
        content=b'[{"title":"Synthetic"}]',
    )
    assert source.status_code == 200 and source.json()['sourceReady'] is True
    assert (
        client.get(
            f'/api/content/v1/types/article/imports/{import_id}', headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f'/api/content/v1/types/article/imports/{import_id}/commit', headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f'/api/content/v1/types/article/imports/{import_id}/cancel', headers=headers
        ).status_code
        == 200
    )

    exported = client.post(
        '/api/content/v1/types/article/exports',
        headers=headers,
        json={'format': 'csv', 'schemaVersion': 1, 'fields': ['title']},
    )
    assert exported.status_code == 201 and exported.json()['status'] == 'queued'
    export_id = exported.json()['id']
    assert (
        client.get(
            f'/api/content/v1/types/article/exports/{export_id}', headers=headers
        ).status_code
        == 200
    )
    download = client.post(
        f'/api/content/v1/types/article/exports/{export_id}/download', headers=headers
    )
    assert download.status_code == 200 and download.json()['expiresIn'] == 60
    content = client.get(
        f'/api/content/v1/types/article/exports/{export_id}/content',
        headers={**headers, 'Download-Grant': 'opaque-download-grant-that-is-long-enough'},
    )
    assert content.status_code == 200 and content.content == b'title\nSynthetic\n'
    assert content.headers['cache-control'] == 'private, no-store'
    assert content.headers['content-disposition'] == 'attachment; filename="workspace-export.csv"'
    assert all(call[1]['site_id'] == 'site-a' for call in FakeJobRepository.calls)


def test_job_creation_rejects_missing_idempotency_and_unknown_or_unsafe_fields():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    endpoint = '/api/content/v1/types/article/imports'
    payload = {
        'sourceSha256': 'b' * 64,
        'schemaVersion': 1,
        'mapping': {'Title': 'title'},
    }
    assert client.post(endpoint, headers=headers, json=payload).status_code == 422
    assert (
        client.post(
            endpoint,
            headers={**headers, 'Idempotency-Key': 'synthetic-request-104'},
            json={**payload, 'command': 'unsafe'},
        ).status_code
        == 422
    )
