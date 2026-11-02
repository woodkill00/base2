"""Exact public-pack keys through validated routes and real restricted-role storage.

The authentication principal is injected and a real generated journey manifest is
selected; tenant parsing, manifest gating, authorization, Pydantic payloads, route
guards and repository transactions remain real. HTTP
serialization is covered separately by test_content_workspace_contract.py.
The existing fixture owns a unique synthetic tenant inside the disposable database;
its runner destroys that entire database, including these immutable definitions,
records and audit rows. Do not delete retained rows or use owner SQL to seed keys.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import HTTPException, Request

from api.db import workspace_db_conn
from api.routes import content_workspace as routes
from api.security.content_workspace import CursorCodec, CursorError
from api.security.request_auth import PublicPrincipal
from api.settings import settings

pytestmark = pytest.mark.integration


@pytest.fixture
def public_family_workspace_fixture(monkeypatch, request):
    # Test-only key, scoped and restored by monkeypatch. Production defaults and
    # CursorCodec's minimum strength remain unchanged. Check before any DB setup.
    monkeypatch.setattr(settings, 'TOKEN_PEPPER', 'synthetic-public-family-cursor-key-124')
    codec = CursorCodec(settings.TOKEN_PEPPER)
    scope = {'site': 'synthetic-family-site', 'type': 'blog-post'}
    position = {'id': 'synthetic-prerequisite'}
    token = codec.encode(scope=scope, position=position, now=100)
    assert codec.decode(token, expected_scope=scope, now=101) == position
    with pytest.raises(CursorError):
        codec.decode(token, expected_scope={**scope, 'site': 'other-site'}, now=101)
    return request.getfixturevalue('workspace_policy_fixture')


@pytest.mark.parametrize('type_key', ['blog-post', 'doc-page', 'portfolio-item'])
def test_public_family_key_validated_routes_persist_exact_scoped_identity(
    public_family_workspace_fixture, monkeypatch, type_key
):
    fixture = public_family_workspace_fixture
    site_id = fixture['site_id']
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / 'site_profiles/journey-reference.json').read_text()
    )
    monkeypatch.setattr(routes, 'SITE_MANIFEST', manifest)
    principal = PublicPrincipal(
        user_id=fixture['reviewer_id'],
        authenticated_at=datetime.now(UTC),
        recently_authenticated=True,
    )
    monkeypatch.setattr(routes, 'require_authenticated_principal', lambda request: principal)

    def request(tenant=site_id):
        return Request(
            {
                'type': 'http',
                'method': 'POST',
                'path': '/api/content/v1/types',
                'headers': [(b'x-tenant-id', tenant.encode('ascii'))],
            }
        )

    # Assert the same role used by the repository is neither owner nor RLS bypass.
    with workspace_db_conn(tenant_id=site_id) as connection, connection.cursor() as cursor:
        cursor.execute(
            'SELECT rolsuper, rolbypassrls, '
            'current_user = pg_get_userbyid((SELECT relowner FROM pg_class '
            "WHERE oid='sitecontent_contenttypedefinition'::regclass)) "
            'FROM pg_roles WHERE rolname=current_user'
        )
        assert cursor.fetchone() == (False, False, False)

    created = routes.create_type(
        routes.DefinitionCreate(
            typeKey=type_key,
            name='Synthetic public family',
            fields=[{'fieldKey': 'summary', 'label': 'Summary', 'fieldKind': 'short_text'}],
        ),
        request(),
    )
    assert created['typeKey'] == type_key
    assert created['siteId'] == site_id
    published = routes.publish_type(
        type_key,
        created['version'],
        routes.DefinitionMutation(expectedLockVersion=created['lockVersion']),
        request(),
    )
    assert published['status'] == 'published'
    definition = routes.get_type(type_key, created['version'], request())
    assert definition['typeKey'] == type_key
    assert definition['siteId'] == site_id

    record = routes.create_record(
        type_key,
        routes.RecordCreate(
            title='Synthetic family entry', slug='family-entry', values={'summary': type_key}
        ),
        request(),
    )
    assert record['typeKey'] == type_key
    assert record['state'] == 'draft'  # Schema publication does not bypass content review.
    listed = routes.list_records(type_key, request(), limit=25, cursor=None, q=None)
    assert [item['id'] for item in listed['items']] == [record['id']]
    assert listed['items'][0]['values'] == {'summary': type_key}
    persisted = fixture['repo'].get_record(
        site_id=site_id, type_key=type_key, record_id=UUID(record['id'])
    )
    assert persisted['typeKey'] == type_key
    assert persisted['id'] == record['id']
    assert persisted['siteId'] == site_id

    # Neither the legacy underscore spelling nor another tenant can read this identity.
    with pytest.raises(ValueError, match='content_not_found'):
        fixture['repo'].get_record(
            site_id=site_id, type_key=type_key.replace('-', '_'), record_id=UUID(record['id'])
        )
    with pytest.raises(ValueError, match='content_not_found'):
        fixture['repo'].get_record(
            site_id='unrelated-site', type_key=type_key, record_id=UUID(record['id'])
        )
    with pytest.raises(HTTPException) as denied:
        routes.get_type(type_key, created['version'], request('unrelated-site'))
    assert denied.value.status_code == 404
