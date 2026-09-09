from contextlib import contextmanager

import pytest

from api.migrations import runner
from api.scripts import migrate


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query):
        assert query == 'SELECT version FROM api_schema_migrations ORDER BY version'

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return Cursor(self.rows)


def test_migrate_cli_applies_and_verifies_exact_ledger(monkeypatch, capsys):
    applied = []

    @contextmanager
    def connection():
        yield Connection([(version,) for version in migrate.MIGRATIONS])

    monkeypatch.setattr(migrate, 'apply_migrations', lambda: applied.append(True))
    monkeypatch.setattr(migrate, 'db_conn', connection)

    assert migrate.main() == 0
    assert applied == [True]


def test_migrate_cli_check_mode_never_applies(monkeypatch, capsys):
    applied = []

    @contextmanager
    def connection():
        yield Connection([(version,) for version in migrate.MIGRATIONS])

    monkeypatch.setattr(migrate, 'apply_migrations', lambda: applied.append(True))
    monkeypatch.setattr(migrate, 'db_conn', connection)

    assert migrate.main(['--check']) == 0
    assert applied == []
    assert capsys.readouterr().out == (
        f'{{"migrationCount": {len(migrate.MIGRATIONS)}, "ok": true, ' '"secretValuesEmitted": 0}\n'
    )


def test_api_migration_disable_switch_is_an_explicit_noop(monkeypatch):
    monkeypatch.setenv('API_DISABLE_MIGRATIONS', 'true')
    monkeypatch.setattr(
        runner,
        'db_conn',
        lambda: pytest.fail('disabled migration unexpectedly opened the database'),
    )
    assert runner.apply_migrations() is None


def test_api_migration_lock_contention_is_bounded_and_fails_closed(monkeypatch):
    class LockedCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, _parameters=None):
            assert 'pg_try_advisory_lock' in query

        def fetchone(self):
            return (False,)

    class LockedConnection:
        autocommit = False

        def cursor(self):
            return LockedCursor()

    @contextmanager
    def connection():
        yield LockedConnection()

    monkeypatch.delenv('API_DISABLE_MIGRATIONS', raising=False)
    monkeypatch.setattr(runner, 'db_conn', connection)
    monkeypatch.setattr(runner.time, 'sleep', lambda _seconds: None)
    with pytest.raises(RuntimeError, match='api_migration_lock_timeout'):
        runner.apply_migrations()
