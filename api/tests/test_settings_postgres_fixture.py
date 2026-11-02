"""Disposable PostgreSQL fixture lifecycle must preserve append-only history."""
from contextlib import contextmanager

import pytest

from api.tests import test_settings_postgres as integration


@pytest.mark.parametrize('body_fails', [False, True])
def test_fixture_retires_only_its_exact_synthetic_owners(monkeypatch, body_fails):
    calls = []
    commits = []

    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, sql, params): calls.append((' '.join(sql.split()), params))

    class Connection:
        def cursor(self): return Cursor()
        def commit(self): commits.append(True)

    @contextmanager
    def connection():
        yield Connection()

    monkeypatch.setattr(integration, 'db_conn', connection)
    fixture = integration.owners.__wrapped__()
    owners = next(fixture)
    assert len(set(owners)) == 2
    if body_fails:
        with pytest.raises(RuntimeError, match='test body failed'):
            fixture.throw(RuntimeError('test body failed'))
    else:
        with pytest.raises(StopIteration):
            next(fixture)
    assert calls == [
        ('INSERT INTO api_auth_users(id,email,password_hash) VALUES (%s,%s,%s)',
         (str(owner), f'{owner}@example.test', 'disabled-synthetic-fixture'))
        for owner in owners
    ] + [
        ('UPDATE api_auth_users SET is_active=FALSE WHERE id=%s', (str(owner),))
        for owner in owners
    ]
    assert len(commits) == 2
