from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import settings


@pytest.fixture
def admitted(monkeypatch):
    principal = SimpleNamespace(user_id=UUID('00000000-0000-0000-0000-000000001121'))
    monkeypatch.setattr(settings, 'require_authenticated_principal', lambda request: principal)
    monkeypatch.setattr(settings, 'require_tenant', lambda request: 'tenant-a')
    monkeypatch.setattr(settings, 'SITE_MANIFEST', {
        'modules': [{'id': name, 'enabled': True} for name in
                    ('accounts', 'content-workspace', 'media', 'commerce', 'community')],
        'locales': ['en'],
    })
    return principal


@pytest.mark.parametrize('role,administrative', [
    ('owner', True), ('admin', True), ('editor', False), ('viewer', False), (None, False),
])
def test_capabilities_use_current_tenant_membership(monkeypatch, admitted, role, administrative):
    calls = []

    def membership(**kwargs):
        calls.append(kwargs)
        return {'role': role} if role else None

    monkeypatch.setattr(settings, 'membership', membership)
    response = TestClient(app).get('/api/settings/capabilities')
    assert response.status_code == 200
    body = response.json()
    ids = {item['id'] for item in body['categories']}
    assert ('organization' in ids) is administrative
    assert ('developer' in ids) is administrative
    assert 'site-capabilities' in ids
    assert calls == [{'user_id': admitted.user_id, 'tenant_id': 'tenant-a'}]
    assert all(item['scope'] == ('account' if item['category'] == 'profile' else 'personal')
               for item in body['controls'] if not item['id'].startswith('workspace-policy.'))
    shared = [item for item in body['controls'] if item['id'].startswith('workspace-policy.')]
    assert len(shared) == (2 if administrative else 1 if role else 0)
    assert all(item['scope'] in {'site','organization'} for item in shared)
    assert all(item['permission']=='workspace-policy.read' for item in shared)
    category_scope = {item['id']: item['scope'] for item in body['categories']}
    assert category_scope['profile'] == category_scope['security'] == 'account'
    assert category_scope['appearance'] == 'personal'
    assert len({item['id'] for item in body['controls']}) == len(body['controls'])
    assert len(body['controls']) >= 15
    assert all(item['category'] in ids for item in body['controls'])
    assert body['locales'] == ['en']


def test_module_catalog_is_manifest_bound_and_does_not_claim_live_engines(monkeypatch, admitted):
    monkeypatch.setattr(settings, 'membership', lambda **kwargs: {'role': 'viewer'})
    body = TestClient(app).get('/api/settings/capabilities').json()
    modules = {item['id']: item for item in body['modules']}
    assert modules['commerce']['enabled'] is True
    assert modules['commerce']['state'] == 'limited'
    assert modules['commerce']['action'] is None
    assert 'live payments' in modules['commerce']['description']
    assert modules['booking']['enabled'] is False
    assert modules['booking']['state'] == 'disabled'
    assert modules['content-workspace']['action']['path'] == '/workspace'
    assert modules['media']['action']['path'] == '/media'
    assert all(item['scope'] == 'site' for item in modules.values())
    assert all(item['managed_by'] == 'deployment' for item in modules.values())


def test_missing_membership_or_disabled_modules_cannot_offer_workspaces(monkeypatch, admitted):
    monkeypatch.setattr(settings, 'membership', lambda **kwargs: None)
    body = TestClient(app).get('/api/settings/capabilities').json()
    assert all(item['action'] is None for item in body['modules'])
    monkeypatch.setattr(settings, 'SITE_MANIFEST', {'modules': [], 'locales': ['en']})
    monkeypatch.setattr(settings, 'membership', lambda **kwargs: pytest.fail('accounts disabled'))
    body = TestClient(app).get('/api/settings/capabilities').json()
    assert all(item['state'] == 'disabled' for item in body['modules'])
    assert {'organization', 'developer'}.isdisjoint(item['id'] for item in body['categories'])


def test_module_registry_matches_checked_in_module_ids():
    from pathlib import Path
    from api.settings_registry import MODULES

    root = Path(__file__).resolve().parents[2]
    known = {path.parent.name for path in (root / 'modules').glob('*/module.json')}
    assert {item['id'] for item in MODULES} <= known
    assert {'commerce', 'community', 'membership', 'subscription', 'support'} <= known
