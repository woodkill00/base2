import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from api.main import app
from api.security.secret_box import SecretBox
from api.services.data_rights import receipt_digest


USER_ID = UUID('00000000-0000-0000-0000-000000000701')
OPERATION_ID = UUID('00000000-0000-0000-0000-000000000702')


def _principal(*, recent: bool = True):
    return SimpleNamespace(
        user_id=USER_ID,
        authenticated_at=datetime.now(timezone.utc),
        recently_authenticated=recent,
    )


def test_export_is_encrypted_durable_and_dispatch_failure_is_visible(monkeypatch):
    key = Fernet.generate_key().decode('ascii')
    captured = {}
    monkeypatch.setattr('api.routes.privacy.settings.IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr(
        'api.routes.privacy.require_authenticated_principal', lambda request: _principal()
    )
    monkeypatch.setattr('api.routes.privacy.insert_audit_event', lambda **kwargs: None)

    def create(**kwargs):
        captured.update(kwargs)
        return OPERATION_ID, True

    monkeypatch.setattr('api.routes.privacy.repository.create_operation', create)
    monkeypatch.setattr(
        'api.tasks.process_data_rights_operation.delay',
        lambda operation_id: (_ for _ in ()).throw(RuntimeError('broker unavailable')),
    )
    response = TestClient(app).post(
        '/api/privacy/export', headers={'X-Tenant-Id': 'tenant-a'}
    )
    assert response.status_code == 202, response.text
    assert response.json() == {
        'accepted': True,
        'operation_id': str(OPERATION_ID),
        'kind': 'export',
        'status': 'queued',
        'dispatch': 'deferred',
        'idempotent': False,
    }
    assert captured['tenant_id'] == 'tenant-a'
    assert captured['user_id'] == USER_ID
    assert captured['request_ciphertext'] != '{"schema_version":1}'
    assert json.loads(SecretBox(key).decrypt(captured['request_ciphertext'])) == {
        'schema_version': 1
    }


def test_active_request_is_idempotently_reused_without_redispatch(monkeypatch):
    key = Fernet.generate_key().decode('ascii')
    monkeypatch.setattr('api.routes.privacy.settings.IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr(
        'api.routes.privacy.require_authenticated_principal', lambda request: _principal()
    )
    monkeypatch.setattr('api.routes.privacy.insert_audit_event', lambda **kwargs: None)
    monkeypatch.setattr(
        'api.routes.privacy.repository.create_operation',
        lambda **kwargs: (OPERATION_ID, False),
    )
    monkeypatch.setattr(
        'api.routes.privacy._dispatch',
        lambda operation_id: (_ for _ in ()).throw(AssertionError('must not dispatch')),
    )
    response = TestClient(app).post(
        '/api/privacy/export', headers={'X-Tenant-Id': 'tenant-a'}
    )
    assert response.status_code == 202
    assert response.json()['dispatch'] == 'already_active'
    assert response.json()['idempotent'] is True


def test_sensitive_requests_require_recent_reauthentication(monkeypatch):
    monkeypatch.setattr(
        'api.routes.privacy.require_authenticated_principal',
        lambda request: _principal(recent=False),
    )
    response = TestClient(app).post(
        '/api/privacy/export', headers={'X-Tenant-Id': 'tenant-a'}
    )
    assert response.status_code == 401
    assert response.json() == {'detail': 'recent_reauthentication_required'}


def test_correction_deactivation_and_deletion_validate_before_storage(monkeypatch):
    monkeypatch.setattr(
        'api.routes.privacy.require_authenticated_principal', lambda request: _principal()
    )
    monkeypatch.setattr(
        'api.routes.privacy.repository.create_operation',
        lambda **kwargs: (_ for _ in ()).throw(AssertionError('must not store')),
    )
    client = TestClient(app)
    headers = {'X-Tenant-Id': 'tenant-a'}
    correction = client.post(
        '/api/privacy/correct', headers=headers, json={'fields': {'role': 'owner'}}
    )
    deletion = client.post(
        '/api/privacy/delete', headers=headers, json={'confirmation': 'yes'}
    )
    deactivation = client.post(
        '/api/privacy/deactivate', headers=headers, json={'confirmation': 'yes'}
    )
    assert correction.status_code == 422
    assert correction.json()['detail'] == 'correction_field_not_allowed'
    assert deletion.status_code == 422
    assert deletion.json()['detail'] == 'deletion_confirmation_invalid'
    assert deactivation.status_code == 422
    assert deactivation.json()['detail'] == 'deactivation_confirmation_invalid'


def test_export_download_is_integrity_checked_and_never_cached(monkeypatch):
    key = Fernet.generate_key().decode('ascii')
    payload = {'schema_version': 1, 'account': {'email': 'owner@example.test'}}
    digest = receipt_digest(
        operation_id=str(OPERATION_ID), tenant_id='tenant-a', user_id=str(USER_ID),
        payload=payload, key='pepper',
    )
    operation = {
        'id': OPERATION_ID, 'kind': 'export', 'status': 'completed',
        'request_ciphertext': 'encrypted',
        'result_ciphertext': SecretBox(key).encrypt(json.dumps(payload)),
        'receipt_digest': digest, 'error_code': '',
        'created_at': datetime.now(timezone.utc), 'completed_at': datetime.now(timezone.utc),
        'retention_until': datetime.now(timezone.utc) + timedelta(days=1),
    }
    monkeypatch.setattr('api.routes.privacy.settings.IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr('api.routes.privacy.settings.TOKEN_PEPPER', 'pepper')
    monkeypatch.setattr(
        'api.routes.privacy.require_authenticated_principal', lambda request: _principal()
    )
    monkeypatch.setattr('api.routes.privacy.repository.owned_operation', lambda **kwargs: operation)
    response = TestClient(app).get(
        f'/api/privacy/operations/{OPERATION_ID}/download',
        headers={'X-Tenant-Id': 'tenant-a'},
    )
    assert response.status_code == 200, response.text
    assert response.json() == payload
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-export-receipt-sha256'] == digest
    operation['receipt_digest'] = '0' * 64
    tampered = TestClient(app).get(
        f'/api/privacy/operations/{OPERATION_ID}/download',
        headers={'X-Tenant-Id': 'tenant-a'},
    )
    assert tampered.status_code == 409
    assert tampered.json()['detail'] == 'export_integrity_failed'


def test_cross_tenant_or_admin_denial_is_generic_not_found(monkeypatch):
    monkeypatch.setattr(
        'api.routes.privacy.require_authenticated_principal', lambda request: _principal()
    )
    monkeypatch.setattr('api.routes.privacy.repository.owned_operation', lambda **kwargs: None)
    monkeypatch.setattr(
        'api.routes.privacy.require_permission',
        lambda **kwargs: (_ for _ in ()).throw(PermissionError('not_found')),
    )
    client = TestClient(app)
    headers = {'X-Tenant-Id': 'tenant-b'}
    owned = client.get(f'/api/privacy/operations/{OPERATION_ID}', headers=headers)
    admin = client.get('/api/privacy/admin/operations', headers=headers)
    assert owned.status_code == admin.status_code == 404
    assert owned.json() == admin.json() == {'detail': 'not_found'}
