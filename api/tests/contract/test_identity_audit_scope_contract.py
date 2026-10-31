from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from api.main import app

USER_ID = UUID('00000000-0000-0000-0000-000000000711')
ORG_ID = UUID('00000000-0000-0000-0000-000000000722')
TARGET_ID = UUID('00000000-0000-0000-0000-000000000733')
FORGED_ORG = '00000000-0000-0000-0000-000000000799'

MUTATIONS = [
    ('post', '/organization/bootstrap', {'name': 'Tenant A'}, 'bootstrap_owner_organization',
     'identity.organization_bootstrapped'),
    ('post', '/invitations/accept', {'token': 'private-invitation-token-value-12345'}, 'accept_invitation',
     'identity.invitation_accepted'),
    ('post', '/admin/invitations', {'email': 'invitee@example.test', 'role': 'editor'}, 'create_invitation',
     'identity.invitation_created'),
    ('delete', f'/admin/invitations/{TARGET_ID}', None, 'revoke_invitation',
     'identity.invitation_revoked'),
    ('patch', f'/admin/members/{TARGET_ID}/role',
     {'role': 'editor', 'expected_updated_at': '2026-10-30T12:00:00Z'}, 'update_member_role',
     'identity.member_role_changed'),
    ('post', '/admin/credentials', {'label': 'automation', 'scopes': ['content.read']}, 'create_api_credential',
     'identity.credential_created'),
    ('delete', f'/admin/credentials/{TARGET_ID}', None, 'revoke_api_credential',
     'identity.credential_revoked'),
]


@pytest.fixture
def scoped_actions(monkeypatch):
    captured = {'audit': [], 'mutation': [], 'permissions': []}
    principal = SimpleNamespace(user_id=USER_ID, authenticated_at=datetime.now(timezone.utc))
    monkeypatch.setattr('api.routes.identity._recent_principal', lambda _request: principal)
    monkeypatch.setattr('api.routes.identity.settings.IDENTITY_ALLOW_FIRST_OWNER_BOOTSTRAP', True)
    monkeypatch.setattr('api.routes.identity.settings.TOKEN_PEPPER', 'fixture-pepper')
    monkeypatch.setattr('api.auth.repo.get_user_by_id', lambda _user_id: SimpleNamespace(email='invitee@example.test'))
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: captured['audit'].append(kwargs))
    monkeypatch.setattr('api.services.email_service.queue_email', lambda **kwargs: None)

    def permission(**kwargs):
        captured['permissions'].append(kwargs)
        return {'organization_id': ORG_ID, 'tenant_id': 'tenant-a', 'role': 'owner'}

    monkeypatch.setattr('api.repositories.identity_admin.require_permission', permission)
    return captured


@pytest.mark.parametrize('method,path,payload,writer,action', MUTATIONS)
def test_organization_audit_uses_authorized_scope_not_payload(
    monkeypatch, scoped_actions, method, path, payload, writer, action,
):
    def mutation(**kwargs):
        scoped_actions['mutation'].append(kwargs)
        if writer in {'bootstrap_owner_organization', 'accept_invitation'}:
            return {'organization_id': ORG_ID, 'role': 'owner'}
        return TARGET_ID if writer in {'create_invitation', 'create_api_credential'} else True

    monkeypatch.setattr(f'api.repositories.identity_admin.{writer}', mutation)
    request_args = {}
    if payload is not None:
        request_args['json'] = {
            **payload, 'organization_id': FORGED_ORG, 'tenant_id': 'forged-tenant',
            'metadata': {'tenant_id': 'forged-tenant', 'organization_id': FORGED_ORG},
        }
    response = TestClient(app).request(
        method, f'/api/identity{path}', headers={'X-Tenant-Id': 'tenant-a'}, **request_args,
    )
    assert response.status_code == 200, response.text
    assert len(scoped_actions['audit']) == 1
    event = scoped_actions['audit'][0]
    assert event['action'] == action
    assert event['user_id'] == USER_ID
    assert event['metadata']['tenant_id'] == 'tenant-a'
    assert event['metadata']['organization_id'] == str(ORG_ID)
    assert FORGED_ORG not in str(event)
    assert 'forged-tenant' not in str(event)
    assert 'private-invitation-token-value' not in str(event)
    assert scoped_actions['mutation'][0]['tenant_id'] == 'tenant-a'
    if scoped_actions['permissions']:
        assert scoped_actions['permissions'][0]['tenant_id'] == 'tenant-a'
        assert scoped_actions['mutation'][0]['organization_id'] == ORG_ID
    if action == 'identity.credential_created':
        assert response.json()['secret'] not in str(event)


@pytest.mark.parametrize('method,path,payload,writer,action', [
    item for item in MUTATIONS if item[3] not in {'create_invitation', 'create_api_credential'}
])
def test_failed_organization_mutation_does_not_write_success_audit(
    monkeypatch, scoped_actions, method, path, payload, writer, action,
):
    monkeypatch.setattr(f'api.repositories.identity_admin.{writer}', lambda **kwargs: None)
    response = TestClient(app).request(
        method, f'/api/identity{path}', headers={'X-Tenant-Id': 'tenant-a'},
        **({'json': payload} if payload is not None else {}),
    )
    assert response.status_code in {404, 409}
    assert scoped_actions['audit'] == []


@pytest.mark.parametrize('method,path,payload,writer,action', [
    item for item in MUTATIONS if item[1].startswith('/admin/')
])
def test_unauthorized_organization_mutation_never_writes_audit(
    monkeypatch, scoped_actions, method, path, payload, writer, action,
):
    def deny(**kwargs):
        raise PermissionError('not_found')

    monkeypatch.setattr('api.repositories.identity_admin.require_permission', deny)
    response = TestClient(app).request(
        method, f'/api/identity{path}', headers={'X-Tenant-Id': 'tenant-a'},
        **({'json': payload} if payload is not None else {}),
    )
    assert response.status_code == 404
    assert response.json() == {'detail': 'not_found'}
    assert scoped_actions['audit'] == []


def test_personal_mfa_enrollment_is_not_assigned_to_current_organization(monkeypatch, scoped_actions):
    monkeypatch.setattr('api.routes.identity.settings.IDENTITY_ENCRYPTION_KEY', Fernet.generate_key().decode())
    monkeypatch.setattr('api.repositories.identity_admin.create_totp_authenticator', lambda **kwargs: TARGET_ID)
    response = TestClient(app).post('/api/identity/mfa/totp/enroll', headers={'X-Tenant-Id': 'tenant-a'})
    assert response.status_code == 200
    assert len(scoped_actions['audit']) == 1
    assert scoped_actions['audit'][0]['action'] == 'identity.totp_enrollment_started'
    assert 'tenant_id' not in scoped_actions['audit'][0].get('metadata', {})
    assert 'organization_id' not in scoped_actions['audit'][0].get('metadata', {})
    assert scoped_actions['permissions'] == []
