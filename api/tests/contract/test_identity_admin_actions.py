from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from api.main import app
from api.security.identity import generate_totp_secret, totp_code
from api.security.secret_box import SecretBox


USER_ID = UUID('00000000-0000-0000-0000-000000000411')
ORG_ID = UUID('00000000-0000-0000-0000-000000000422')
AUTH_ID = UUID('00000000-0000-0000-0000-000000000433')


def principal():
    return SimpleNamespace(user_id=USER_ID, authenticated_at=datetime.now(timezone.utc))


def test_totp_enrollment_encrypts_at_rest_and_confirmation_shows_recovery_once(monkeypatch):
    key = Fernet.generate_key().decode('ascii')
    captured = {}
    secret = generate_totp_secret()
    monkeypatch.setattr('api.routes.identity.settings.IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr('api.routes.identity.settings.TOKEN_PEPPER', 'test-pepper')
    monkeypatch.setattr('api.routes.identity._recent_principal', lambda request: principal())
    monkeypatch.setattr(
        'api.auth.repo.get_user_by_id',
        lambda user_id: SimpleNamespace(email='owner@example.test'),
    )
    monkeypatch.setattr('api.routes.identity.generate_totp_secret', lambda: secret)
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)

    def create_authenticator(*, user_id, ciphertext):
        captured['ciphertext'] = ciphertext
        assert user_id == USER_ID
        return AUTH_ID

    monkeypatch.setattr(
        'api.repositories.identity_admin.create_totp_authenticator', create_authenticator
    )
    client = TestClient(app)
    started = client.post('/api/identity/mfa/totp/enroll')
    assert started.status_code == 200, started.text
    assert secret in started.json()['otpauth_uri']
    assert secret not in captured['ciphertext']
    assert SecretBox(key).decrypt(captured['ciphertext']) == secret

    monkeypatch.setattr(
        'api.repositories.identity_admin.pending_totp',
        lambda **kwargs: captured['ciphertext'],
    )

    def activate(**kwargs):
        captured['hashes'] = kwargs['code_hashes']
        return True

    monkeypatch.setattr(
        'api.repositories.identity_admin.activate_totp_with_recovery_codes', activate
    )
    confirmed = client.post(
        '/api/identity/mfa/totp/confirm',
        json={'authenticator_id': str(AUTH_ID), 'code': totp_code(secret)},
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body['shown_once'] is True
    assert len(body['recovery_codes']) == len(captured['hashes']) == 8
    assert not set(body['recovery_codes']) & set(captured['hashes'])


def test_invitation_never_returns_token_and_credential_secret_is_one_time(monkeypatch):
    member = {'organization_id': ORG_ID, 'role': 'owner'}
    monkeypatch.setattr('api.routes.identity._recent_principal', lambda request: principal())
    monkeypatch.setattr(
        'api.repositories.identity_admin.require_permission', lambda **kwargs: member
    )
    monkeypatch.setattr(
        'api.repositories.identity_admin.create_invitation', lambda **kwargs: AUTH_ID
    )
    monkeypatch.setattr(
        'api.repositories.identity_admin.create_api_credential', lambda **kwargs: AUTH_ID
    )
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)
    monkeypatch.setattr(
        'api.services.email_service.queue_email', lambda **kwargs: SimpleNamespace(id=AUTH_ID)
    )
    monkeypatch.setattr('api.routes.identity.settings.TOKEN_PEPPER', 'test-pepper')
    client = TestClient(app)
    headers = {'X-Tenant-Id': 'tenant-a'}

    invitation = client.post(
        '/api/identity/admin/invitations',
        headers=headers,
        json={'email': 'invitee@example.test', 'role': 'editor'},
    )
    assert invitation.status_code == 200, invitation.text
    assert invitation.json() == {'id': str(AUTH_ID), 'status': 'queued_for_delivery'}
    assert 'token' not in invitation.text.lower()

    credential = client.post(
        '/api/identity/admin/credentials',
        headers=headers,
        json={'label': 'automation', 'scopes': ['content.read']},
    )
    assert credential.status_code == 200, credential.text
    body = credential.json()
    assert body['shown_once'] is True
    assert body['secret'].startswith(body['prefix'] + '.')
    assert 'secret_hash' not in body


def test_admin_denial_is_timing_safe_generic_not_found(monkeypatch):
    monkeypatch.setattr(
        'api.routes.identity.require_authenticated_principal', lambda request: principal()
    )
    monkeypatch.setattr(
        'api.repositories.identity_admin.admin_overview',
        lambda **kwargs: (_ for _ in ()).throw(PermissionError('not_found')),
    )
    response = TestClient(app).get(
        '/api/identity/admin/overview', headers={'X-Tenant-Id': 'tenant-a'}
    )
    assert response.status_code == 404
    assert response.json() == {'detail': 'not_found'}


def test_invalid_roles_and_scopes_fail_before_repository_calls(monkeypatch):
    monkeypatch.setattr('api.routes.identity._recent_principal', lambda request: principal())
    client = TestClient(app)
    headers = {'X-Tenant-Id': 'tenant-a'}
    invalid_role = client.post(
        '/api/identity/admin/invitations',
        headers=headers,
        json={'email': 'invitee@example.test', 'role': 'owner'},
    )
    assert invalid_role.status_code == 422
    assert invalid_role.json()['detail'] == 'invalid_role'
    invalid_scope = client.post(
        '/api/identity/admin/credentials',
        headers=headers,
        json={'label': 'unsafe', 'scopes': ['admin.*']},
    )
    assert invalid_scope.status_code == 422
    assert invalid_scope.json()['detail'] == 'invalid_scopes'


def test_invitation_acceptance_is_account_email_and_tenant_bound(monkeypatch):
    captured = {}
    monkeypatch.setattr('api.routes.identity._recent_principal', lambda request: principal())
    monkeypatch.setattr(
        'api.auth.repo.get_user_by_id',
        lambda user_id: SimpleNamespace(email='invitee@example.test'),
    )
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)

    def accept(**kwargs):
        captured.update(kwargs)
        return {'organization_id': ORG_ID, 'role': 'editor'}

    monkeypatch.setattr('api.repositories.identity_admin.accept_invitation', accept)
    response = TestClient(app).post(
        '/api/identity/invitations/accept',
        headers={'X-Tenant-Id': 'tenant-a'},
        json={'token': 'x' * 40},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {'organization_id': str(ORG_ID), 'role': 'editor'}
    assert captured['user_id'] == USER_ID
    assert captured['user_email'] == 'invitee@example.test'
    assert captured['tenant_id'] == 'tenant-a'
    assert captured['token_hash'] != 'x' * 40


def test_admin_revocations_are_exact_tenant_owned_actions(monkeypatch):
    member = {'organization_id': ORG_ID, 'role': 'owner'}
    calls = []
    monkeypatch.setattr('api.routes.identity._recent_principal', lambda request: principal())
    monkeypatch.setattr('api.repositories.identity_admin.require_permission', lambda **kwargs: member)
    monkeypatch.setattr(
        'api.repositories.identity_admin.revoke_invitation',
        lambda **kwargs: calls.append(('invitation', kwargs)) or True,
    )
    monkeypatch.setattr(
        'api.repositories.identity_admin.revoke_api_credential',
        lambda **kwargs: calls.append(('credential', kwargs)) or True,
    )
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)
    client = TestClient(app)
    headers = {'X-Tenant-Id': 'tenant-a'}
    invitation = client.delete(f'/api/identity/admin/invitations/{AUTH_ID}', headers=headers)
    credential = client.delete(f'/api/identity/admin/credentials/{AUTH_ID}', headers=headers)
    assert invitation.json() == {'revoked': True}
    assert credential.json() == {'revoked': True}
    assert all(call[1]['organization_id'] == ORG_ID for call in calls)


def test_role_change_maps_last_owner_and_stale_write_without_mutation(monkeypatch):
    member = {'organization_id': ORG_ID, 'role': 'owner'}
    monkeypatch.setattr('api.routes.identity._recent_principal', lambda request: principal())
    monkeypatch.setattr('api.repositories.identity_admin.require_permission', lambda **kwargs: member)
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)
    client = TestClient(app)
    payload = {'role': 'admin', 'expected_updated_at': '2026-08-25T12:00:00Z'}
    monkeypatch.setattr(
        'api.repositories.identity_admin.update_member_role',
        lambda **kwargs: (_ for _ in ()).throw(ValueError('last_owner')),
    )
    last_owner = client.patch(
        f'/api/identity/admin/members/{USER_ID}/role',
        headers={'X-Tenant-Id': 'tenant-a'},
        json=payload,
    )
    assert last_owner.status_code == 409
    assert last_owner.json()['detail'] == 'last_owner_required'
    monkeypatch.setattr('api.repositories.identity_admin.update_member_role', lambda **kwargs: False)
    stale = client.patch(
        f'/api/identity/admin/members/{USER_ID}/role',
        headers={'X-Tenant-Id': 'tenant-a'},
        json=payload,
    )
    assert stale.status_code == 409
    assert stale.json()['detail'] == 'membership_changed'


def test_recovery_regeneration_requires_current_totp_and_shows_codes_once(monkeypatch):
    key = Fernet.generate_key().decode('ascii')
    secret = generate_totp_secret()
    captured = {}
    monkeypatch.setattr('api.routes.identity._recent_principal', lambda request: principal())
    monkeypatch.setattr('api.routes.identity.settings.IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr('api.routes.identity.settings.TOKEN_PEPPER', 'test-pepper')
    monkeypatch.setattr(
        'api.repositories.identity_admin.active_totp',
        lambda **kwargs: {'id': AUTH_ID, 'secret_ciphertext': SecretBox(key).encrypt(secret)},
    )
    monkeypatch.setattr(
        'api.repositories.identity_admin.replace_recovery_codes',
        lambda **kwargs: captured.update(kwargs),
    )
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)
    response = TestClient(app).post(
        '/api/identity/mfa/recovery-codes/regenerate',
        json={'code': totp_code(secret)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['shown_once'] is True
    assert len(body['recovery_codes']) == len(captured['code_hashes']) == 8
    assert not set(body['recovery_codes']) & set(captured['code_hashes'])


def test_first_owner_bootstrap_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(
        'api.routes.identity.settings.IDENTITY_ALLOW_FIRST_OWNER_BOOTSTRAP', False
    )
    response = TestClient(app).post(
        '/api/identity/organization/bootstrap',
        headers={'X-Tenant-Id': 'tenant-a'},
        json={'name': 'Tenant A'},
    )
    assert response.status_code == 404
    assert response.json() == {'detail': 'not_found'}
