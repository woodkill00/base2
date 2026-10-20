"""Synthetic logout tests: no credentials, provider calls or live database."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('api.routes.auth.settings.AUTH_REFRESH_COOKIE', True)
    monkeypatch.setattr('api.routes.auth.settings.ENV', 'development')
    monkeypatch.setattr('api.routes.auth.settings.COOKIE_SECURE', False)
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: None)
    instance = TestClient(app)
    instance.cookies.set('app_refresh', 'synthetic-refresh')
    instance.cookies.set('app_csrf', 'synthetic-csrf')
    return instance


@pytest.mark.parametrize('step', ['find', 'revoke'])
def test_repository_failure_is_not_reported_as_success(client, monkeypatch, step):
    find = Mock(return_value={'id': 'synthetic', 'user_id': None})
    revoke = Mock()
    (find if step == 'find' else revoke).side_effect = RuntimeError('private database detail')
    monkeypatch.setattr('api.auth.repo.find_refresh_token', find)
    monkeypatch.setattr('api.auth.repo.revoke_refresh_token', revoke)
    result = client.post('/api/auth/logout', headers={'X-CSRF-Token': 'synthetic-csrf'})
    assert result.status_code == 503
    assert result.json() == {'detail': 'Logout could not be confirmed'}
    assert 'private database detail' not in result.text
    assert 'set-cookie' not in result.headers


@pytest.mark.parametrize('found', [True, False])
def test_revoked_or_already_absent_session_clears_cookie(client, monkeypatch, found):
    monkeypatch.setattr(
        'api.auth.repo.find_refresh_token', lambda **kwargs: {'id': 'synthetic'} if found else None
    )
    revoke = Mock()
    monkeypatch.setattr('api.auth.repo.revoke_refresh_token', revoke)
    result = client.post('/api/auth/logout', headers={'X-CSRF-Token': 'synthetic-csrf'})
    assert result.status_code == 204
    assert 'Max-Age=0' in result.headers['set-cookie']
    assert revoke.call_count == int(found)


def test_missing_csrf_never_attempts_revocation(client, monkeypatch):
    find = Mock()
    monkeypatch.setattr('api.auth.repo.find_refresh_token', find)
    result = client.post('/api/auth/logout')
    assert result.status_code == 403
    find.assert_not_called()
