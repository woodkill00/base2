from uuid import UUID
from contextlib import contextmanager

from fastapi.testclient import TestClient

from api.main import app


USER_ID = UUID('00000000-0000-0000-0000-000000000111')
SESSION_ID = UUID('00000000-0000-0000-0000-000000000222')


def test_revoke_exact_owned_session_and_write_redacted_audit(monkeypatch):
    calls = []
    monkeypatch.setattr('api.security.request_auth.require_authenticated_user', lambda request: USER_ID)
    monkeypatch.setattr(
        'api.auth.repo.revoke_user_refresh_token',
        lambda *, user_id, token_id: calls.append((user_id, token_id)) or True,
    )
    monkeypatch.setattr('api.auth.repo.insert_audit_event', lambda **kwargs: calls.append(kwargs))

    response = TestClient(app).post(f'/api/auth/sessions/{SESSION_ID}/revoke')

    assert response.status_code == 204
    assert calls[0] == (USER_ID, SESSION_ID)
    assert calls[1]['action'] == 'auth.revoke_session'
    assert calls[1]['metadata'] == {'session_id': str(SESSION_ID)}


def test_revoke_session_hides_invalid_foreign_and_already_revoked_identity(monkeypatch):
    monkeypatch.setattr('api.security.request_auth.require_authenticated_user', lambda request: USER_ID)
    monkeypatch.setattr('api.auth.repo.revoke_user_refresh_token', lambda **kwargs: False)
    client = TestClient(app)

    for value in ('not-a-uuid', str(SESSION_ID)):
        response = client.post(f'/api/auth/sessions/{value}/revoke')
        assert response.status_code == 404
        assert response.json() == {'detail': 'session_not_found'}


def test_repository_revocation_is_owner_bound_and_active_only(monkeypatch):
    from api.auth.repo import revoke_user_refresh_token

    class Cursor:
        rowcount = 1

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params):
            normalized = ' '.join(query.split())
            assert 'WHERE id=%s AND user_id=%s AND revoked_at IS NULL' in normalized
            assert 'expires_at > NOW()' in normalized
            assert params == (str(SESSION_ID), str(USER_ID))

    class Connection:
        autocommit = False

        def cursor(self):
            return Cursor()

    @contextmanager
    def fake_db_conn():
        yield Connection()

    monkeypatch.setattr('api.auth.repo.db_conn', fake_db_conn)
    assert revoke_user_refresh_token(user_id=USER_ID, token_id=SESSION_ID) is True
