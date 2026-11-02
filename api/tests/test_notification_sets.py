"""Whole-set notification CAS regressions (Feature 124)."""
from contextlib import contextmanager
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.repositories import settings as repo
from api.routes.settings import NotificationUpdate

USER = uuid4()


class Cursor:
    def __init__(self, *, version=None, winner=True, existing=(), fail_audit=False):
        self.version, self.winner = version, winner
        self.existing, self.saved, self.calls = list(existing), [], []
        self.result = None
        self.rowcount = 1
        self.fail_audit = fail_audit
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=()):
        sql = ' '.join(sql.split())
        self.calls.append((sql, params))
        if sql.startswith('SELECT version'):
            self.result = (self.version,) if self.version is not None else None
        elif 'INSERT INTO api_notification_preference_sets' in sql:
            self.result = (1, 1) if self.winner else None
            self.rowcount = int(self.winner)
        elif 'UPDATE api_notification_preference_sets' in sql:
            self.result = (1, self.version + 1)
        elif 'SELECT event_family' in sql:
            self.result = self.saved or self.existing
        elif 'INSERT INTO api_notification_preferences' in sql:
            self.saved.append((*params[3:7], 'now'))
        elif 'INSERT INTO api_auth_audit_events' in sql and self.fail_audit:
            raise RuntimeError('audit_unavailable')
    def fetchone(self): return self.result
    def fetchall(self): return self.result


class Connection:
    def __init__(self, cursor): self.value, self.commits, self.rollbacks = cursor, 0, 0
    def cursor(self): return self.value
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


def bind(monkeypatch, cursor):
    connection = Connection(cursor)
    @contextmanager
    def db_conn(*, tenant_id=None):
        assert tenant_id == 'tenant-a'
        yield connection
    monkeypatch.setattr(repo, 'db_conn', db_conn)
    return connection


def test_notification_write_requires_closed_nonnegative_version():
    with pytest.raises(ValidationError):
        NotificationUpdate.model_validate({'preferences': []})
    for version in (-1, True, '1'):
        with pytest.raises(ValidationError):
            NotificationUpdate.model_validate({'preferences': [], 'expected_version': version})
    assert NotificationUpdate(preferences=[], expected_version=0).expected_version == 0


@pytest.mark.parametrize('version,expected,winner', [(3, 2, True), (None, 1, True), (None, 0, False)])
def test_stale_and_first_insert_loser_never_replace_or_audit(monkeypatch, version, expected, winner):
    cur = Cursor(version=version, winner=winner)
    conn = bind(monkeypatch, cur)
    assert repo.replace_notifications(user_id=USER, tenant_id='tenant-a', expected_version=expected, preferences=[]) is None
    assert conn.commits == 0 and conn.rollbacks == 1
    assert not any('DELETE' in sql or 'api_auth_audit_events' in sql for sql, _ in cur.calls)


def test_empty_first_save_inserts_required_rows_returns_own_snapshot(monkeypatch):
    cur = Cursor()
    conn = bind(monkeypatch, cur)
    monkeypatch.setattr(repo, 'list_notifications', lambda **_: pytest.fail('post-commit reread'))
    result = repo.replace_notifications(user_id=USER, tenant_id='tenant-a', expected_version=0, preferences=[])
    assert result['version'] == result['schema_version'] == 1
    assert {(r['event_family'], r['delivery'], r['mandatory']) for r in result['preferences']} == {
        ('security', 'immediate', True), ('transactional', 'immediate', True)}
    assert conn.commits == 1
    assert any('api_auth_audit_events' in sql for sql, _ in cur.calls)
    assert all(params[1] == 'tenant-a' for sql, params in cur.calls if sql.startswith('DELETE'))


def test_replacement_preserves_omitted_mandatory_channels_but_not_optional(monkeypatch):
    cur = Cursor(version=4, existing=[('security', 'email', 'digest', True, 'old'),
        ('transactional', 'browser', 'immediate', True, 'old'), ('marketing', 'email', 'digest', False, 'old')])
    bind(monkeypatch, cur)
    result = repo.replace_notifications(user_id=USER, tenant_id='tenant-a', expected_version=4, preferences=[])
    assert result['version'] == 5
    choices = {(r['event_family'], r['channel']): r['delivery'] for r in result['preferences']}
    assert choices == {('security','email'): 'digest', ('transactional','browser'): 'immediate', ('transactional','email'): 'immediate'}


def test_audit_failure_rolls_back_entire_replacement(monkeypatch):
    conn = bind(monkeypatch, Cursor(fail_audit=True))
    with pytest.raises(RuntimeError, match='audit_unavailable'):
        repo.replace_notifications(user_id=USER, tenant_id='tenant-a', expected_version=0, preferences=[])
    assert conn.commits == 0 and conn.rollbacks == 1


@pytest.mark.parametrize('rows,version,preferences', [([], 0, 0), ([(1, 3, None, None, None, None, None)], 3, 0),
    ([(1, 2, 'product', 'email', 'digest', False, 'now')], 2, 1)])
def test_read_is_single_coherent_aggregate_statement(monkeypatch, rows, version, preferences):
    cur = Cursor()
    cur.result = rows
    bind(monkeypatch, cur)
    result = repo.get_notifications(user_id=USER, tenant_id='tenant-a')
    assert result['version'] == version and len(result['preferences']) == preferences
    assert len(cur.calls) == 1
    assert 'LEFT JOIN api_notification_preferences' in cur.calls[0][0]


def test_unsupported_schema_does_not_masquerade_as_missing(monkeypatch):
    cur = Cursor()
    cur.result = [(2, 1, None, None, None, None, None)]
    bind(monkeypatch, cur)
    with pytest.raises(ValueError, match='settings_schema_unsupported'):
        repo.get_notifications(user_id=USER, tenant_id='tenant-a')


@pytest.mark.parametrize('preferences', [
    [{'event_family': 'security', 'channel': 'email', 'delivery': 'disabled', 'mandatory': False}],
    [{'event_family': 'unknown', 'channel': 'email', 'delivery': 'digest'}],
    [{'event_family': 'product', 'channel': 'email', 'delivery': 'digest'}] * 2,
])
def test_repository_does_not_trust_caller_mandatory_classification(monkeypatch, preferences):
    conn = bind(monkeypatch, Cursor())
    with pytest.raises(ValueError, match='settings_notification_'):
        repo.replace_notifications(user_id=USER, tenant_id='tenant-a', expected_version=0, preferences=preferences)
    assert conn.commits == 0 and conn.rollbacks == 1


def test_version_validation_precedes_database_access(monkeypatch):
    monkeypatch.setattr(repo, 'db_conn', lambda **_: pytest.fail('must not enter DB'))
    with pytest.raises(ValueError, match='settings_version_invalid'):
        repo.replace_notifications(user_id=USER, tenant_id='tenant-a', expected_version=-1, preferences=[])


def test_django_adapter_sql_is_exact_runtime_mirror():
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    path = root / 'django/api_schema/migrations/0006_notification_preference_sets.py'
    tree = ast.parse(path.read_text())
    adapter_sql = next(ast.literal_eval(node.value) for node in tree.body
                       if isinstance(node, ast.Assign) and any(
                           isinstance(target, ast.Name) and target.id == 'FORWARD_SQL' for target in node.targets))
    sql = (root / 'api/migrations/sql/014_create_notification_preference_sets.sql').read_text()
    assert adapter_sql.strip() == sql.strip()
    assert 'version BIGINT' in sql and 'ON CONFLICT (user_id, tenant_id) DO NOTHING' in sql


def test_legacy_list_reader_delegates_to_coherent_set(monkeypatch):
    monkeypatch.setattr(repo, 'get_notifications', lambda **kwargs: {'preferences': [{'event_family': 'product'}]})
    assert repo.list_notifications(user_id=USER, tenant_id='tenant-a') == [{'event_family': 'product'}]
