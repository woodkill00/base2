"""Dormant authorization-code path boundaries; not GIS or PKCE acceptance."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import auth, oauth
from api.services import oauth_google


@pytest.mark.parametrize(
    'path,payload',
    [
        ('/api/oauth/google/start', {'return_path': '/account'}),
        ('/api/oauth/google/callback', {'code': 'synthetic', 'state': 'synthetic'}),
    ],
)
@pytest.mark.parametrize('enabled,status', [(False, 404), (True, 503)])
def test_disabled_or_missing_code_configuration_never_exchanges(
    monkeypatch, path, payload, enabled, status
):
    monkeypatch.setattr(oauth.settings, 'GOOGLE_OAUTH_ENABLED', enabled)
    monkeypatch.setattr(oauth.settings, 'GOOGLE_OAUTH_CLIENT_ID', 'synthetic-client')
    monkeypatch.setattr(oauth.settings, 'GOOGLE_OAUTH_CLIENT_SECRET', None)
    exchange = AsyncMock(side_effect=AssertionError('provider must not be contacted'))
    monkeypatch.setattr(oauth_google, 'exchange_google_authorization_code', exchange)
    response = TestClient(app).post(path, json=payload)
    assert response.status_code == status
    assert 'set-cookie' not in response.headers
    exchange.assert_not_called()


def test_provider_denial_creates_no_identity_or_session(monkeypatch):
    for name, value in {
        'GOOGLE_OAUTH_ENABLED': True,
        'GOOGLE_OAUTH_CLIENT_ID': 'synthetic-client',
        'GOOGLE_OAUTH_CLIENT_SECRET': 'synthetic-secret',
        'GOOGLE_OAUTH_REDIRECT_URI': 'https://testserver/api/oauth/google/callback',
        'OAUTH_STATE_SECRET': 's' * 32,
        'COOKIE_SECURE': True,
    }.items():
        monkeypatch.setattr(oauth.settings, name, value)
    exchange = AsyncMock(side_effect=ValueError('sensitive provider detail'))
    complete = AsyncMock(side_effect=AssertionError('identity must not be created'))
    monkeypatch.setattr(oauth_google, 'exchange_google_authorization_code', exchange)
    monkeypatch.setattr(auth, 'complete_google_oauth_identity', complete)
    client = TestClient(app, base_url='https://testserver')
    start = client.post('/api/oauth/google/start', json={'return_path': '/account'})
    assert start.status_code == 200
    response = client.post(
        '/api/oauth/google/callback',
        json={'code': 'synthetic-code', 'state': start.json()['state']},
    )
    assert response.status_code == 401
    assert response.json() == {'detail': 'oauth_rejected'}
    assert 'set-cookie' not in response.headers
    exchange.assert_awaited_once()
    complete.assert_not_called()
