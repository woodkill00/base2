from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from api.scripts import ensure_owner as owner


class Cursor:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows


@pytest.fixture
def fixture(monkeypatch):
    monkeypatch.setattr(
        owner, 'load_runtime_manifest', lambda: ({'siteId': 'base2-obsidian'}, 'digest')
    )
    cursor = Cursor([])
    conn = SimpleNamespace(cursor=lambda: cursor, commit=lambda: None)

    @contextmanager
    def db():
        yield conn

    monkeypatch.setattr(owner, 'db_conn', db)
    monkeypatch.setattr(owner, 'hash_password', lambda _: 'synthetic-hash')
    return cursor


def provision():
    return owner.ensure_owner(
        email='owner@example.test',
        password='ExampleTest123!',
        display_name='synthetic-owner',
        profile='base2-obsidian',
    )


def test_created_uses_existing_schema_without_verification_or_privilege_changes(fixture):
    assert provision() == 'created'
    insert = fixture.calls[-1]
    assert 'INSERT INTO api_auth_users' in insert[0]
    assert insert[1][2] == 'synthetic-hash'
    assert 'verified' not in insert[0] and 'role' not in insert[0]
    assert 'advisory_xact_lock' in fixture.calls[0][0]


def test_existing_preserves_all_security_state(fixture):
    fixture.rows = [('owner@example.test', 'synthetic-owner', True)]
    assert provision() == 'existing-preserved'
    assert all(
        not any(x in sql for x in ('INSERT', 'UPDATE api', 'DELETE')) for sql, _ in fixture.calls
    )


@pytest.mark.parametrize(
    'rows',
    [
        [('owner@example.test', 'someone-else', True)],
        [('owner@example.test', 'synthetic-owner', False)],
        [('other@example.test', 'synthetic-owner', True)],
        [
            ('owner@example.test', 'synthetic-owner', True),
            ('other@example.test', 'synthetic-owner', True),
        ],
    ],
)
def test_collisions_and_disabled_owner_fail_closed(fixture, rows):
    fixture.rows = rows
    with pytest.raises(ValueError, match='owner_identity_conflict'):
        provision()


def test_profile_mismatch_never_opens_database(monkeypatch, fixture):
    monkeypatch.setattr(
        owner, 'load_runtime_manifest', lambda: ({'siteId': 'another-site'}, 'digest')
    )
    with pytest.raises(ValueError, match='environment'):
        provision()
    assert fixture.calls == []


def test_disabled_does_not_read_secret(monkeypatch, capsys):
    monkeypatch.delenv('BASE2_OWNER_ENABLED', raising=False)
    assert owner.main() == 0
    assert 'disabled' in capsys.readouterr().out


def test_failure_never_emits_exception_or_credentials(monkeypatch, capsys):
    monkeypatch.setenv('BASE2_OWNER_ENABLED', 'true')
    monkeypatch.setenv('BASE2_OWNER_FILE', '/missing/private')
    monkeypatch.setattr(owner.sys, 'argv', ['ensure_owner'])
    assert owner.main() == 1
    output = capsys.readouterr().out
    assert 'blocked' in output and '/missing' not in output
