from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import auth
from api.security import google_challenge
from api.services import oauth_google


@pytest.fixture
def flow(monkeypatch):
    store = {}
    redis = MagicMock()
    redis.set.side_effect = lambda key, value, **kwargs: store.setdefault(key, value)
    redis.getdel.side_effect = lambda key: store.pop(key, None)
    monkeypatch.setattr(google_challenge.redis_client, 'get_client', lambda: redis)
    monkeypatch.setattr(auth.settings, 'GOOGLE_OAUTH_ENABLED', True)
    monkeypatch.setattr(auth.settings, 'GOOGLE_OAUTH_CLIENT_ID', 'test-client')
    monkeypatch.setattr(auth.settings, 'COOKIE_SECURE', True)
    monkeypatch.setattr(auth.rate_limit, 'incr_and_check_detailed', lambda *args: (1, False, 0))
    complete = MagicMock()

    async def finish(**kwargs):
        complete(**kwargs)
        return {'authenticated': True}

    monkeypatch.setattr(auth, 'complete_google_oauth_identity', finish)

    def verify(*, id_token, audience, expected_nonce):
        assert audience == 'test-client'
        if id_token != expected_nonce:
            raise ValueError('invalid_nonce')
        return oauth_google.GoogleIdentity('synthetic', 'test@example.invalid', True, '', '')

    monkeypatch.setattr(oauth_google, 'verify_google_id_token', verify)
    return TestClient(app, base_url='https://testserver'), store, complete


def test_cookie_binding_and_one_use_exchange(flow):
    client, store, complete = flow
    response = client.post('/api/auth/oauth/google/challenge')
    assert response.status_code == 200
    cookie = response.headers['set-cookie'].lower()
    for field in (
        'httponly',
        'secure',
        'samesite=strict',
        'max-age=300',
        'path=/api/auth/oauth/google',
    ):
        assert field in cookie
    assert response.headers['cache-control'] == 'no-store'
    nonce = response.json()['nonce']
    assert client.post('/api/auth/oauth/google', json={'credential': nonce}).status_code == 200
    assert not store
    assert client.post('/api/auth/oauth/google', json={'credential': nonce}).status_code == 401
    assert complete.call_count == 1


@pytest.mark.parametrize('case', ['wrong-browser', 'expired', 'nonce-mismatch'])
def test_rejected_binding_never_creates_session(flow, case):
    client, store, complete = flow
    nonce = client.post('/api/auth/oauth/google/challenge').json()['nonce']
    if case == 'wrong-browser':
        client.cookies.clear()
    elif case == 'expired':
        store.clear()
    else:
        nonce = 'wrong-token-nonce'
    response = client.post('/api/auth/oauth/google', json={'credential': nonce})
    assert response.status_code == 401
    complete.assert_not_called()
    assert 'set-cookie' not in response.headers


def test_unavailable_store_never_falls_back(flow, monkeypatch):
    client, _, complete = flow
    client.post('/api/auth/oauth/google/challenge')
    monkeypatch.setattr(
        google_challenge.redis_client, 'get_client', MagicMock(side_effect=ValueError('private'))
    )
    for path, body in [
        ('/api/auth/oauth/google/challenge', {}),
        ('/api/auth/oauth/google', {'credential': 'token'}),
    ]:
        response = client.post(path, json=body)
        assert response.status_code == 503
        assert 'private' not in response.text
    complete.assert_not_called()


def test_disabled_and_rate_limited_challenge_do_not_write(flow, monkeypatch):
    client, store, _ = flow
    monkeypatch.setattr(auth.settings, 'GOOGLE_OAUTH_ENABLED', False)
    assert client.post('/api/auth/oauth/google/challenge').status_code == 404
    assert not store
    monkeypatch.setattr(auth.settings, 'GOOGLE_OAUTH_ENABLED', True)
    monkeypatch.setattr(auth.rate_limit, 'incr_and_check_detailed', lambda *args: (31, True, 60))
    response = client.post('/api/auth/oauth/google/challenge')
    assert response.status_code == 429
    assert response.headers['retry-after'] == '60'
    assert not store


def test_non_object_payload_is_rejected(flow):
    client, _, complete = flow
    assert client.post('/api/auth/oauth/google', json=['bad']).status_code == 400
    complete.assert_not_called()
