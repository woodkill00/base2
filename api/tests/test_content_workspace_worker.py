from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID
from datetime import UTC, datetime

import pytest

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


def test_due_index_records_are_restart_discoverable_ordered_and_bounded(monkeypatch):
    record_id = UUID(int=105)
    cursor = Cursor([('site-a', record_id, 7)])
    bind(monkeypatch, Connection(cursor))

    assert worker.due_index_records(limit=25) == [('site-a', str(record_id), 7)]
    sql = cursor.calls[0][0]
    assert 'LEFT JOIN sitecontent_searchdocument' in sql
    assert 'ORDER BY c.updated_at, c.id LIMIT %s' in sql
    with pytest.raises(ValueError, match='content_limit_exceeded'):
        worker.due_index_records(limit=0)


def test_search_projection_is_closed_and_never_indexes_private_values():
    updated_at = datetime(2026, 9, 2, tzinfo=UTC)
    projection = worker.build_search_projection(
        content_type='article',
        slug='safe-title',
        title='Safe title',
        body='Public body',
        state='published',
        search_visible=True,
        updated_at=updated_at,
        deleted_at=None,
    )
    assert projection == {
        'title': 'Safe title',
        'body': 'Public body',
        'url_path': '/article/safe-title',
        'visibility': 'public',
        'source_updated_at': updated_at,
        'tombstoned': False,
    }
    assert 'values' not in projection

    private = worker.build_search_projection(
        content_type='article',
        slug='draft',
        title='Draft',
        body='Private',
        state='draft',
        search_visible=True,
        updated_at=updated_at,
        deleted_at=None,
    )
    assert private['visibility'] == 'private'
    assert private['tombstoned'] is False


def test_index_worker_is_tenant_bound_replay_safe_and_rejects_future_job(monkeypatch):
    record_id = UUID(int=106)
    updated_at = datetime(2026, 9, 2, tzinfo=UTC)
    row = (
        record_id,
        'article',
        'safe-title',
        'Safe title',
        'Public body',
        'published',
        True,
        updated_at,
        None,
        7,
    )
    cursor = Cursor([row, None])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    assert worker.index_workspace_record(site_id='site-a', record_id=record_id, job_version=7) == (
        'indexed'
    )
    assert scopes == ['site-a'] and connection.commits == 1
    sql = ' '.join(statement for statement, _ in cursor.calls)
    assert 'FOR UPDATE' in sql
    assert 'ON CONFLICT (content_id)' in sql
    assert 'sitecontent_workspaceauditevent' in sql

    stale_cursor = Cursor([row])
    stale_connection = Connection(stale_cursor)
    bind(monkeypatch, stale_connection)
    assert worker.index_workspace_record(
        site_id='site-a', record_id=record_id, job_version=6
    ) == 'stale_job'
    assert stale_connection.commits == 0

    future_cursor = Cursor([row])
    future_connection = Connection(future_cursor)
    bind(monkeypatch, future_connection)
    with pytest.raises(ValueError, match='content_index_version_invalid'):
        worker.index_workspace_record(site_id='site-a', record_id=record_id, job_version=8)
    assert future_connection.rollbacks == 1
