from contextlib import contextmanager

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
