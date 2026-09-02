from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import content_workspace
from api.security.request_auth import PublicPrincipal


class FakeRecordRepository:
    calls: list[tuple[str, dict]] = []

    def list_records(self, **kwargs):
        self.calls.append(('list', kwargs))
        return {'items': [], 'nextCursor': None}

    def get_record(self, **kwargs):
        self.calls.append(('detail', kwargs))
        return {
            'id': str(kwargs['record_id']),
            'siteId': kwargs['site_id'],
            'typeKey': kwargs['type_key'],
            'version': 3,
            'state': 'draft',
        }

    def create_record(self, **kwargs):
        self.calls.append(('create', kwargs))
        return {
            'id': '00000000-0000-0000-0000-000000003104',
            'version': 1,
            'state': 'draft',
            'siteId': kwargs['site_id'],
        }

    def update_record(self, **kwargs):
        self.calls.append(('update', kwargs))
        return {
            'id': str(kwargs['record_id']),
            'version': kwargs['expected_version'] + 1,
            'state': 'draft',
        }

    def transition_record(self, **kwargs):
        self.calls.append(('transition', kwargs))
        return {
            'id': str(kwargs['record_id']),
            'version': kwargs['expected_version'] + 1,
            'state': 'in_review',
        }

    def soft_delete_record(self, **kwargs):
        self.calls.append(('delete', kwargs))
        return {
            'id': str(kwargs['record_id']),
            'version': kwargs['expected_version'] + 1,
            'state': 'deleted',
        }

    def list_versions(self, **kwargs):
        self.calls.append(('versions', kwargs))
        return {'items': [{'version': 1, 'snapshotSha256': 'a' * 64}]}

    def restore_record(self, **kwargs):
        self.calls.append(('restore', kwargs))
        return {
            'id': str(kwargs['record_id']),
            'version': kwargs['expected_version'] + 1,
            'state': 'draft',
        }

    def list_views(self, **kwargs):
        self.calls.append(('views', kwargs))
        return {'items': []}

    def create_view(self, **kwargs):
        self.calls.append(('view-create', kwargs))
        return {
            'id': '00000000-0000-0000-0000-000000004104',
            'visibility': kwargs['payload']['visibility'],
        }

    def get_view(self, **kwargs):
        self.calls.append(('view-detail', kwargs))
        return {'id': str(kwargs['view_id']), 'lockVersion': 1, 'visibility': 'private'}

    def update_view(self, **kwargs):
        self.calls.append(('view-update', kwargs))
        return {'id': str(kwargs['view_id']), 'lockVersion': kwargs['expected_version'] + 1}

    def delete_view(self, **kwargs):
        self.calls.append(('view-delete', kwargs))
        return {'id': str(kwargs['view_id']), 'deleted': True}

    def execute_view(self, **kwargs):
        self.calls.append(('view-execute', kwargs))
        return {'items': [], 'nextCursor': None}


@pytest.fixture(autouse=True)
def scoped(monkeypatch):
    FakeRecordRepository.calls = []
    principal = PublicPrincipal(UUID(int=104), datetime.now(UTC), True)
    monkeypatch.setattr(
        content_workspace, 'require_authenticated_principal', lambda request: principal
    )
    monkeypatch.setattr(content_workspace, 'require_tenant', lambda request: 'site-a')
    monkeypatch.setattr(content_workspace, 'workspace_enabled', lambda: True)
    monkeypatch.setattr(content_workspace, 'authorize', lambda **kwargs: None)
    monkeypatch.setattr(content_workspace, 'get_repository', lambda: FakeRecordRepository())


def test_record_create_update_transition_delete_bind_scope_and_versions():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    created = client.post(
        '/api/content/v1/types/article/records',
        headers=headers,
        json={'slug': 'hello', 'title': 'Hello', 'values': {'title': 'Hello'}},
    )
    assert created.status_code == 201
    record_id = created.json()['id']
    updated = client.patch(
        f'/api/content/v1/types/article/records/{record_id}',
        headers={**headers, 'If-Match': '"1"'},
        json={'values': {'title': 'Updated'}},
    )
    assert updated.status_code == 200 and updated.json()['version'] == 2
    transitioned = client.post(
        f'/api/content/v1/types/article/records/{record_id}/transitions/submit_review',
        headers=headers,
        json={'expectedVersion': 2},
    )
    assert transitioned.status_code == 200
    deleted = client.delete(
        f'/api/content/v1/types/article/records/{record_id}?expected_version=3', headers=headers
    )
    assert deleted.status_code == 200 and deleted.json()['state'] == 'deleted'
    assert all(call[1]['site_id'] == 'site-a' for call in FakeRecordRepository.calls)


def test_record_queries_and_mutations_fail_closed_on_unbounded_or_unknown_input():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    assert (
        client.get('/api/content/v1/types/article/records?limit=101', headers=headers).status_code
        == 422
    )
    assert (
        client.post(
            '/api/content/v1/types/article/records',
            headers=headers,
            json={'slug': 'hello', 'title': 'Hello', 'values': {}, 'command': 'rm'},
        ).status_code
        == 422
    )
    queried = client.get(
        '/api/content/v1/types/article/records',
        headers=headers,
        params={
            'q': '{"filters":[{"field":"title","operator":"contains","value":"safe"}],'
            '"sort":["slug"],"fields":["title"],"expand":[],"limit":10}'
        },
    )
    assert queried.status_code == 200
    assert FakeRecordRepository.calls[-1][1]['query']['fields'] == ['title']
    assert (
        client.get(
            '/api/content/v1/types/article/records', headers=headers, params={'q': '{bad'}
        ).status_code
        == 422
    )
    record_id = '00000000-0000-0000-0000-000000003104'
    assert (
        client.patch(
            f'/api/content/v1/types/article/records/{record_id}',
            headers=headers,
            json={'values': {}},
        ).status_code
        == 428
    )
    assert (
        client.post(
            f'/api/content/v1/types/article/records/{record_id}/transitions/execute_shell',
            headers=headers,
            json={'expectedVersion': 1},
        ).status_code
        == 422
    )


def test_schedule_rejects_unknown_timezone_before_repository_execution():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    response = client.post(
        '/api/content/v1/types/article/records/'
        '00000000-0000-0000-0000-000000003104/transitions/schedule',
        headers=headers,
        json={
            'expectedVersion': 1,
            'publishAt': '2030-01-01T12:00:00Z',
            'timezone': 'Mars/Olympus',
        },
    )
    assert response.status_code == 422
    assert FakeRecordRepository.calls == []


def test_privileged_transitions_require_their_specific_permission(monkeypatch):
    permissions = []

    def capture(**kwargs):
        permissions.append(kwargs['permission'])
        return {'role': 'owner'}

    monkeypatch.setattr(content_workspace, 'authorize', capture)
    client = TestClient(app)
    response = client.post(
        '/api/content/v1/types/article/records/'
        '00000000-0000-0000-0000-000000003104/transitions/publish',
        headers={'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'},
        json={'expectedVersion': 1},
    )
    assert response.status_code == 200
    assert permissions == ['content-workspace.publish']


def test_history_restore_and_saved_views_remain_scoped_and_closed():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    record_id = '00000000-0000-0000-0000-000000003104'
    history = client.get(
        f'/api/content/v1/types/article/records/{record_id}/versions', headers=headers
    )
    assert history.status_code == 200 and history.json()['items'][0]['version'] == 1
    restored = client.post(
        f'/api/content/v1/types/article/records/{record_id}/versions/1/restore',
        headers=headers,
        json={'expectedVersion': 4},
    )
    assert restored.status_code == 200 and restored.json()['version'] == 5
    view = client.post(
        '/api/content/v1/types/article/views',
        headers=headers,
        json={
            'title': 'Recent',
            'query': {
                'filters': [{'field': 'title', 'operator': 'contains', 'value': 'safe'}],
                'sort': ['slug'],
                'fields': ['title'],
                'expand': [],
                'limit': 25,
            },
        },
    )
    assert view.status_code == 201 and view.json()['visibility'] == 'private'
    assert client.get('/api/content/v1/types/article/views', headers=headers).status_code == 200
    unsafe = client.post(
        '/api/content/v1/types/article/views',
        headers=headers,
        json={'title': 'Unsafe', 'query': {'sql': 'select secrets'}},
    )
    assert unsafe.status_code == 422


def test_record_detail_and_saved_view_lifecycle_are_owner_and_version_bound():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    record_id = '00000000-0000-0000-0000-000000003104'
    view_id = '00000000-0000-0000-0000-000000004104'
    detail = client.get(f'/api/content/v1/types/article/records/{record_id}', headers=headers)
    assert detail.status_code == 200 and detail.json()['version'] == 3
    assert (
        client.get(f'/api/content/v1/types/article/views/{view_id}', headers=headers).status_code
        == 200
    )
    changed = client.patch(
        f'/api/content/v1/types/article/views/{view_id}',
        headers={**headers, 'If-Match': '"1"'},
        json={'title': 'Changed'},
    )
    assert changed.status_code == 200 and changed.json()['lockVersion'] == 2
    assert (
        client.post(
            f'/api/content/v1/types/article/views/{view_id}/execute', headers=headers
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f'/api/content/v1/types/article/views/{view_id}?expected_version=2', headers=headers
        ).status_code
        == 200
    )
    assert all(call[1]['site_id'] == 'site-a' for call in FakeRecordRepository.calls)


def test_saved_view_patch_requires_optimistic_version_and_rejects_unknown_keys():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    view_id = '00000000-0000-0000-0000-000000004104'
    endpoint = f'/api/content/v1/types/article/views/{view_id}'
    assert client.patch(endpoint, headers=headers, json={'title': 'Changed'}).status_code == 428
    assert (
        client.patch(
            endpoint,
            headers={**headers, 'If-Match': '"1"'},
            json={'title': 'Changed', 'command': 'unsafe'},
        ).status_code
        == 422
    )
