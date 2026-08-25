from datetime import datetime, timedelta, timezone
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from api.auth.repo import User
from api.auth.service import AuthTokens
from api.main import app
from api.security.identity import generate_totp_secret, totp_code
from api.security.secret_box import SecretBox
import pytest


USER_ID = UUID('00000000-0000-0000-0000-000000000611')
AUTH_ID = UUID('00000000-0000-0000-0000-000000000622')
CHALLENGE_ID = UUID('00000000-0000-0000-0000-000000000633')


@pytest.fixture(autouse=True)
def _bounded_rate_limit(monkeypatch):
    monkeypatch.setattr(
        'api.routes.auth.rate_limit.incr_and_check_detailed', lambda *args: (1, False, 0)
    )


def _user():
    return User(
        id=USER_ID,
        email='owner@example.test',
        password_hash='',
        is_active=True,
        is_email_verified=True,
        display_name='',
        avatar_url='',
        bio='',
    )


def _tokens(prefix='provisional'):
    return AuthTokens(
        access_token=f'{prefix}-access',
        refresh_token=f'{prefix}-refresh',
        refresh_token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )


def test_password_login_with_active_totp_returns_only_bounded_challenge(monkeypatch):
    user = _user()
    captured = {}
    monkeypatch.setattr('api.auth.service.login_user', lambda **kwargs: (user, _tokens()))
    monkeypatch.setattr(
        'api.repositories.identity_admin.active_totp',
        lambda **kwargs: {'id': AUTH_ID, 'secret_ciphertext': 'encrypted'},
    )
    monkeypatch.setattr(
        'api.auth.repo.find_refresh_token',
        lambda **kwargs: {'id': CHALLENGE_ID, 'user_id': USER_ID},
    )
    monkeypatch.setattr(
        'api.auth.repo.revoke_refresh_token',
        lambda **kwargs: captured.setdefault('revoked', kwargs['token_id']),
    )
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)

    def create_challenge(**kwargs):
        captured.update(kwargs)
        return CHALLENGE_ID

    monkeypatch.setattr(
        'api.repositories.identity_admin.create_login_challenge', create_challenge
    )
    response = TestClient(app).post(
        '/api/auth/login', json={'email': user.email, 'password': 'Password1'}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['mfa_required'] is True
    assert body['methods'] == ['totp', 'recovery_code']
    assert body['expires_in'] == 300
    assert body['challenge_token']
    assert 'access_token' not in body
    assert 'refresh_token' not in body
    assert captured['revoked'] == CHALLENGE_ID
    assert captured['token_hash'] != body['challenge_token']


def test_totp_challenge_is_ip_bound_consumed_once_then_issues_fresh_session(monkeypatch):
    key = Fernet.generate_key().decode('ascii')
    secret = generate_totp_secret()
    user = _user()
    issued = _tokens('final')
    captured = {}
    monkeypatch.setattr('api.routes.auth.settings.IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr(
        'api.repositories.identity_admin.pending_login_challenge',
        lambda **kwargs: {
            'id': CHALLENGE_ID,
            'user_id': USER_ID,
            'ip': 'testclient',
            'user_agent': 'testclient',
        },
    )
    monkeypatch.setattr(
        'api.repositories.identity_admin.active_totp',
        lambda **kwargs: {
            'id': AUTH_ID,
            'secret_ciphertext': SecretBox(key).encrypt(secret),
        },
    )
    monkeypatch.setattr(
        'api.repositories.identity_admin.consume_login_challenge',
        lambda **kwargs: captured.setdefault('consumed', kwargs['challenge_id']) == CHALLENGE_ID,
    )
    monkeypatch.setattr('api.auth.repo.get_user_by_id', lambda user_id: user)
    monkeypatch.setattr(
        'api.auth.service.issue_authenticated_session', lambda **kwargs: issued
    )
    response = TestClient(app).post(
        '/api/auth/login/mfa',
        json={'challenge_token': 'challenge', 'code': totp_code(secret)},
    )
    assert response.status_code == 200, response.text
    assert response.json()['access_token'] == 'final-access'
    assert captured['consumed'] == CHALLENGE_ID


def test_invalid_or_cross_ip_challenge_returns_generic_error_and_no_session(monkeypatch):
    monkeypatch.setattr(
        'api.repositories.identity_admin.pending_login_challenge',
        lambda **kwargs: {
            'id': CHALLENGE_ID,
            'user_id': USER_ID,
            'ip': 'different-client',
            'user_agent': '',
        },
    )
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)
    issued = []
    monkeypatch.setattr(
        'api.auth.service.issue_authenticated_session', lambda **kwargs: issued.append(kwargs)
    )
    response = TestClient(app).post(
        '/api/auth/login/mfa',
        json={'challenge_token': 'challenge', 'code': '000000'},
    )
    assert response.status_code == 401
    assert response.json() == {'detail': 'Invalid authentication challenge'}
    assert issued == []
