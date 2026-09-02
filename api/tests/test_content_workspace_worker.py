from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

from api.services import content_workspace_worker as worker


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        self.calls.append((' '.join(sql.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        return list(self.rows)


class Connection:
    def __init__(self, cursor):
        self.cursor_value, self.commits, self.rollbacks = cursor, 0, 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def bind(monkeypatch, connection):
    scopes = []

    @contextmanager
    def fake_db_conn(*, tenant_id=None):
        scopes.append(tenant_id)
        yield connection

    monkeypatch.setattr(worker, 'db_conn', fake_db_conn)
    return scopes


def test_due_publications_are_ordered_and_bounded(monkeypatch):
    cursor = Cursor([('site-a', UUID(int=104))])
    bind(monkeypatch, Connection(cursor))
    assert worker.due_publication_ids(limit=25) == [('site-a', str(UUID(int=104)))]
    assert 'ORDER BY publish_at, id LIMIT %s' in cursor.calls[0][0]


def test_publication_is_tenant_bound_transactional_and_replay_safe(monkeypatch):
    record_id = UUID(int=104)
    cursor = Cursor([(record_id, 3, 1, {'title': 'Safe'}, 'scheduled', 'future'), (True,)])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)
    assert worker.publish_scheduled_record(site_id='site-a', record_id=record_id) == 'published'
    assert scopes == ['site-a'] and connection.commits == 1
    sql = ' '.join(statement for statement, _ in cursor.calls)
    assert 'FOR UPDATE' in sql and 'sitecontent_contentrevision' in sql
    assert 'sitecontent_workspaceauditevent' in sql

    replay_cursor = Cursor([(record_id, 4, 1, {}, 'published', None)])
    replay = Connection(replay_cursor)
    bind(monkeypatch, replay)
    assert (
        worker.publish_scheduled_record(site_id='site-a', record_id=record_id)
        == 'already_published'
    )
    assert all('UPDATE sitecontent_contentrecord' not in call[0] for call in replay_cursor.calls)
