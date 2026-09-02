from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import app
from api.routes import content_workspace
from api.security.request_auth import PublicPrincipal


USER_ID = UUID('00000000-0000-0000-0000-000000001104')


class FakeRepository:
    def list_definitions(self, **kwargs):
        return {'items': [], 'nextCursor': None, 'scope': kwargs['site_id']}

    def create_definition(self, **kwargs):
        return {
            'id': '00000000-0000-0000-0000-000000002104',
            'siteId': kwargs['site_id'],
            'typeKey': kwargs['payload']['type_key'],
            'version': 1,
            'status': 'draft',
            'lockVersion': 1,
        }


@pytest.fixture(autouse=True)
def authenticated(monkeypatch):
    principal = PublicPrincipal(
        user_id=USER_ID,
        authenticated_at=datetime.now(UTC),
        recently_authenticated=True,
    )
    monkeypatch.setattr(
        content_workspace, 'require_authenticated_principal', lambda request: principal
    )
    monkeypatch.setattr(content_workspace, 'require_tenant', lambda request: 'site-a')
    monkeypatch.setattr(content_workspace, 'authorize', lambda **kwargs: None)
    monkeypatch.setattr(content_workspace, 'get_repository', lambda: FakeRepository())


def test_definition_schema_rejects_unknown_and_executable_fields():
    with pytest.raises(ValidationError):
        content_workspace.DefinitionCreate.model_validate(
            {'typeKey': 'article', 'name': 'Article', 'python': "print('unsafe')"}
        )
    with pytest.raises(ValidationError):
        content_workspace.FieldDefinition.model_validate(
            {
                'fieldKey': 'title',
                'label': 'Title',
                'fieldKind': 'python',
            }
        )


def test_capabilities_are_closed_bounded_and_do_not_expose_secrets():
    response = TestClient(app).get(
        '/api/content/v1/capabilities',
        headers={'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['schemaVersion'] == 1
    assert 'python' not in body['fieldKinds']
    assert body['limits']['maximumPageSize'] <= 100
    assert not {'token', 'password', 'storageKey'} & set(body)


def test_definition_list_and_create_are_tenant_bound(monkeypatch):
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    listed = client.get('/api/content/v1/types', headers=headers)
    assert listed.status_code == 200
    assert listed.json()['scope'] == 'site-a'

    created = client.post(
        '/api/content/v1/types',
        headers=headers,
        json={
            'typeKey': 'article',
            'name': 'Article',
            'fields': [
                {
                    'fieldKey': 'title',
                    'label': 'Title',
                    'fieldKind': 'short_text',
                    'required': True,
                }
            ],
        },
    )
    assert created.status_code == 201
    assert created.json()['siteId'] == 'site-a'


def test_unknown_body_key_and_unbounded_page_fail_closed():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    invalid = client.post(
        '/api/content/v1/types',
        headers=headers,
        json={'typeKey': 'article', 'name': 'Article', 'sql': 'select 1'},
    )
    assert invalid.status_code == 422
    assert client.get('/api/content/v1/types?limit=101', headers=headers).status_code == 422
