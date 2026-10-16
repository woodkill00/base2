from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
import io
import json
import pytest
from api.scripts import preview_media_fixture as fixture

NOW = datetime(2026, 10, 16, tzinfo=UTC)


def config():
    return {
        'run_id': 'base2-full-20261016-000000',
        'expires_at': (NOW + timedelta(minutes=30)).isoformat(),
        'password': 'FixtureOnly123!',
    }


@pytest.fixture
def database(monkeypatch):
    state = {'rows': [None, None], 'calls': [], 'committed': False, 'rolled_back': False}

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def execute(self, sql, values=()):
            state['calls'].append((sql, values))

        def fetchone(self):
            return state['rows'].pop(0)

    def commit():
        state['committed'] = True

    @contextmanager
    def db(**kwargs):
        assert kwargs == {'tenant_id': 'base2-obsidian'}
        try:
            yield SimpleNamespace(cursor=Cursor, commit=commit)
        except Exception:
            state['rolled_back'] = True
            raise

    monkeypatch.setattr(fixture, 'db_conn', db)
    monkeypatch.setattr(
        fixture, 'load_runtime_manifest', lambda: ({'siteId': 'base2-obsidian'}, 'digest')
    )
    monkeypatch.setattr(fixture, 'hash_password', lambda _: 'hashed-fixture')
    return state


def test_fixture_creates_only_synthetic_editor(database):
    assert fixture.provision(config(), now=NOW)['role'] == 'editor'
    assert database['committed']
    sql = ' '.join(row[0] for row in database['calls'])
    assert "'editor','active'" in sql
    assert all(word not in sql for word in ('UPDATE', 'DELETE', 'GRANT', 'owner'))
    assert 'media-base2-full-20261016-000000@example.invalid' in database['calls'][3][1]


@pytest.mark.parametrize('rows', [[('existing',)], [None, ('existing',)]])
def test_collisions_never_modify_existing_data(database, rows):
    database['rows'] = rows
    with pytest.raises(ValueError, match='existing'):
        fixture.provision(config(), now=NOW)
    assert not database['committed'] and database['rolled_back']
    assert not any('INSERT' in sql for sql, _ in database['calls'])


@pytest.mark.parametrize(
    'change',
    [
        {'run_id': 'hostile'},
        {'expires_at': NOW.isoformat()},
        {'expires_at': (NOW + timedelta(hours=2)).isoformat()},
        {'extra': True},
        {'password': 'short'},
    ],
)
def test_invalid_input_never_opens_database(database, change):
    with pytest.raises(ValueError):
        fixture.provision({**config(), **change}, now=NOW)
    assert not database['calls']


def test_default_disabled_never_reads_input(monkeypatch, capsys):
    monkeypatch.delenv('BASE2_PREVIEW_MEDIA_FIXTURE', raising=False)
    assert fixture.main() == 1
    assert 'disabled' in capsys.readouterr().out


@pytest.mark.parametrize('mode', ['success', 'error', 'oversize', 'arguments'])
def test_cli_never_emits_private_input(monkeypatch, capsys, mode):
    monkeypatch.setenv('BASE2_PREVIEW_MEDIA_FIXTURE', 'true')
    monkeypatch.setattr(
        fixture.sys, 'argv', ['fixture'] + (['forbidden'] if mode == 'arguments' else [])
    )
    monkeypatch.setattr(
        fixture.sys,
        'stdin',
        io.StringIO('x' * 4097 if mode == 'oversize' else json.dumps(config())),
    )

    def provision(value):
        if mode == 'error':
            raise ValueError('PRIVATE_FIXTURE_DIAGNOSTIC')
        return {'status': 'created', 'role': 'editor', 'secretValuesEmitted': 0}

    monkeypatch.setattr(fixture, 'provision', provision)
    assert fixture.main() == (0 if mode == 'success' else 1)
    output = capsys.readouterr().out
    assert 'PRIVATE_FIXTURE' not in output and config()['password'] not in output


def test_wrong_profile_never_opens_database(database, monkeypatch):
    monkeypatch.setattr(fixture, 'load_runtime_manifest', lambda: ({'siteId': 'other'}, 'digest'))
    with pytest.raises(ValueError, match='profile'):
        fixture.provision(config(), now=NOW)
    assert not database['calls']
