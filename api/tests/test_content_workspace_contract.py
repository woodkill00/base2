from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import app
from api.routes import content_workspace
from api.security.request_auth import PublicPrincipal


ORIGINAL_WORKSPACE_ENABLED = content_workspace.workspace_enabled

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

    def get_definition(self, **kwargs):
        return {
            'siteId': kwargs['site_id'],
            'typeKey': kwargs['type_key'],
            'version': kwargs['version'],
            'status': 'draft',
            'lockVersion': 1,
        }

    def preview_definition(self, **kwargs):
        return {'classification': 'additive', 'digest': 'a' * 64, 'mutated': False}

    def publish_definition(self, **kwargs):
        return {
            'typeKey': kwargs['type_key'],
            'version': kwargs['version'],
            'status': 'published',
            'lockVersion': 2,
        }

    def retire_definition(self, **kwargs):
        return {
            'typeKey': kwargs['type_key'],
            'version': kwargs['version'],
            'status': 'retired',
            'lockVersion': 3,
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
    monkeypatch.setattr(content_workspace, 'workspace_enabled', lambda: True)
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


def test_disabled_workspace_exposes_no_working_route(monkeypatch):
    monkeypatch.setattr(content_workspace, 'workspace_enabled', lambda: False)
    response = TestClient(app).get(
        '/api/content/v1/capabilities',
        headers={'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'},
    )
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'content_capability_disabled'


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
    envelope = invalid.json()
    assert envelope['error']['code'] == 'content_schema_invalid'
    assert envelope['error']['retryable'] is False
    assert 'input' not in str(envelope['error']['field_issues'])


def test_definition_lifecycle_requires_expected_lock_and_explicit_lossy_confirmation():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}
    base = '/api/content/v1/types/article/versions/1'
    assert client.get(base, headers=headers).status_code == 200
    preview = client.post(f'{base}/preview', headers=headers)
    assert preview.status_code == 200 and preview.json()['mutated'] is False
    assert client.post(f'{base}/publish', headers=headers, json={}).status_code == 422
    published = client.post(
        f'{base}/publish', headers=headers, json={'expectedLockVersion': 1, 'confirmLossy': False}
    )
    assert published.status_code == 200 and published.json()['status'] == 'published'
    retired = client.post(f'{base}/retire', headers=headers, json={'expectedLockVersion': 2})
    assert retired.status_code == 200 and retired.json()['status'] == 'retired'


@pytest.mark.parametrize(
    'key', ['blog-post', 'doc-page', 'portfolio-item', 'old_type', 'a_', 'a' * 63]
)
def test_public_family_type_create_and_version_route_preserve_exact_key(key):
    client = TestClient(app)
    created = client.post('/api/content/v1/types', json={'typeKey': key, 'name': 'Family'})
    assert created.status_code == 201
    assert created.json()['typeKey'] == key
    read = client.get(f'/api/content/v1/types/{key}/versions/1')
    assert read.status_code == 200
    assert read.json()['typeKey'] == key


@pytest.mark.parametrize(
    'key',
    [
        'a',
        'a' * 64,
        'Blog-post',
        '-blog',
        'blog-',
        'blog--post',
        'blog-_post',
        '../blog',
        'blog/post',
        'blog\\post',
        'blog post',
        'blog;drop',
        "blog'post",
        'blog\n',
        'blög',
        'blog\u200bpost',
        'blog%2fpost',
    ],
)
def test_unsafe_type_keys_rejected_by_create_and_route_guard(key):
    from fastapi import HTTPException

    with pytest.raises(ValidationError):
        content_workspace.DefinitionCreate(typeKey=key, name='Family')
    with pytest.raises(HTTPException) as rejected:
        content_workspace._valid_type_key(key)
    assert rejected.value.status_code == 422


@pytest.mark.parametrize('key', ['blog-post', 'doc-page', 'portfolio-item'])
def test_type_compatibility_does_not_widen_field_or_preset_keys(key):
    with pytest.raises(ValidationError):
        content_workspace.DefinitionCreate(typeKey=key, name='Family', presetId=key)
    with pytest.raises(ValidationError):
        content_workspace.FieldDefinition(fieldKey=key, label='Field', fieldKind='short_text')


@pytest.mark.parametrize('key', ['blog-post', 'doc-page', 'portfolio-item'])
def test_public_family_types_do_not_bypass_disabled_workspace(monkeypatch, key):
    monkeypatch.setattr(content_workspace, 'workspace_enabled', lambda: False)
    client = TestClient(app)
    assert (
        client.post('/api/content/v1/types', json={'typeKey': key, 'name': 'Family'}).status_code
        == 404
    )
    assert client.get(f'/api/content/v1/types/{key}/versions/1').status_code == 404


@pytest.mark.parametrize('key', ['blog-post', 'doc-page', 'portfolio-item', 'old_type'])
def test_relationship_target_type_uses_type_key_contract(key):
    field = content_workspace.FieldDefinition(
        fieldKey='related', label='Related', fieldKind='reference', validation={'targetType': key}
    )
    assert field.validation['targetType'] == key


@pytest.mark.parametrize('key', ['blog--post', '../blog', 'Blog', 'blog\\post', 'blog\n', 'a' * 64])
def test_relationship_target_type_rejects_unsafe_keys(key):
    with pytest.raises(ValidationError):
        content_workspace.FieldDefinition(
            fieldKey='related',
            label='Related',
            fieldKind='reference',
            validation={'targetType': key},
        )


@pytest.mark.parametrize(
    'profile,enabled',
    [
        ('journey-reference', True),
        ('base2-obsidian', True),
        ('ember-studio', False),
        ('northstar-library', False),
    ],
)
def test_generated_manifest_still_governs_family_type_discovery_and_routes(
    monkeypatch, profile, enabled
):
    import json
    from pathlib import Path

    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / 'site_profiles' / f'{profile}.json').read_text()
    )
    monkeypatch.setattr(content_workspace, 'SITE_MANIFEST', manifest)
    monkeypatch.setattr(content_workspace, 'workspace_enabled', ORIGINAL_WORKSPACE_ENABLED)
    assert content_workspace.workspace_enabled() is enabled
    client = TestClient(app)
    assert client.get('/api/content/v1/capabilities').status_code == (200 if enabled else 404)
    for key in ('blog-post', 'doc-page', 'portfolio-item'):
        assert client.post(
            '/api/content/v1/types', json={'typeKey': key, 'name': 'Family'}
        ).status_code == (201 if enabled else 404)
        assert client.get(f'/api/content/v1/types/{key}/versions/1').status_code == (
            200 if enabled else 404
        )
