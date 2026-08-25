from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID

import pytest

from api.repositories.site_content import PostgresSiteContentRepository
from api.services.site_content import SiteContentService


class RecordingRepository:
    def __init__(self):
        self.kwargs = None

    def list_content(self, **kwargs):
        self.kwargs = kwargs
        return {'items': [], 'nextCursor': None}

    def submit_form(self, **kwargs):
        self.kwargs = kwargs
        return {'status': 'queued'}


def test_service_validates_cursor_and_binds_form_digest_and_retention():
    repository = RecordingRepository()
    service = SiteContentService(repository)
    with pytest.raises(ValueError, match='invalid_cursor'):
        service.list_content(site_id='site-a', limit=10, cursor='not-a-uuid')

    service.submit_form(
        site_id='site-a',
        form_key='contact',
        replay_key='request-1',
        payload={'message': 'hello'},
        consent={'essential': True},
        request_id='req-1',
    )
    assert repository.kwargs['site_id'] == 'site-a'
    assert repository.kwargs['retention_days'] == 90
    assert len(repository.kwargs['request_digest']) == 64


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params):
        self.executions.append((' '.join(sql.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)
        self.autocommit = None
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def connection_context(connection):
    @contextmanager
    def context():
        yield connection

    return context


def test_repository_creates_submission_and_outbox_in_one_transaction():
    connection = FakeConnection([None])
    repository = PostgresSiteContentRepository()
    with patch('api.repositories.site_content.db_conn', connection_context(connection)):
        receipt = repository.submit_form(
            site_id='site-a',
            form_key='contact',
            replay_key='request-1',
            payload={'message': 'hello'},
            consent={},
            request_id='req-1',
            retention_days=90,
            request_digest='a' * 64,
        )
    sql = '\n'.join(item[0] for item in connection.cursor_instance.executions)
    assert 'INSERT INTO sitecontent_formsubmission' in sql
    assert 'INSERT INTO sitecontent_formdeliveryoutbox' in sql
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert receipt['replayed'] is False


def test_repository_replay_is_noop_and_digest_mismatch_fails_closed():
    existing = (UUID('22222222-2222-4222-8222-222222222222'), 'queued', datetime.now(UTC), 'a' * 64)
    repository = PostgresSiteContentRepository()
    connection = FakeConnection([existing])
    with patch('api.repositories.site_content.db_conn', connection_context(connection)):
        receipt = repository.submit_form(
            site_id='site-a',
            form_key='contact',
            replay_key='request-1',
            payload={},
            consent={},
            request_id='req-1',
            retention_days=90,
            request_digest='a' * 64,
        )
    assert receipt['replayed'] is True
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert len(connection.cursor_instance.executions) == 1

    mismatch = FakeConnection([existing])
    with (
        patch('api.repositories.site_content.db_conn', connection_context(mismatch)),
        pytest.raises(ValueError, match='idempotency_conflict'),
    ):
        repository.submit_form(
            site_id='site-a',
            form_key='contact',
            replay_key='request-1',
            payload={},
            consent={},
            request_id='req-1',
            retention_days=90,
            request_digest='b' * 64,
        )
    assert mismatch.commits == 0
    assert mismatch.rollbacks >= 1
