from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID

import pytest

from api.repositories.site_content import PostgresSiteContentRepository
from api.services.site_content import SiteContentService
from api.site_manifest import load_runtime_manifest


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
    manifest, _ = load_runtime_manifest()
    assert repository.kwargs['retention_days'] == manifest['contact']['retentionDays']
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

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)
        self.autocommit = None
        self.commits = 0
        self.rollbacks = 0
        self.tenant_ids = []

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def connection_context(connection):
    @contextmanager
    def context(*, tenant_id=None):
        connection.tenant_ids.append(tenant_id)
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
    assert connection.autocommit is None
    assert connection.tenant_ids == ['site-a']
    assert receipt['replayed'] is False


def test_community_post_uses_tenant_transaction_without_autocommit_switch():
    connection = FakeConnection([])
    repository = PostgresSiteContentRepository()
    with patch('api.repositories.site_content.db_conn', connection_context(connection)):
        result = repository.create_community_post(
            site_id='site-a',
            author_ref='owner-a',
            payload={'title': 'Hello', 'body': 'World', 'abuseScore': 0},
        )
    assert result['moderationStatus'] == 'pending'
    assert connection.commits == 1
    assert connection.autocommit is None
    assert connection.tenant_ids == ['site-a']


def test_repository_reads_are_tenant_bound_and_map_public_rows():
    now = datetime.now(UTC)
    content_id = UUID('11111111-1111-4111-8111-111111111111')
    content_row = (content_id, 'page', 'about', 'About', 'Excerpt', 'Body', {}, now, now)
    repository = PostgresSiteContentRepository()

    listed = FakeConnection([content_row, content_row])
    with patch('api.repositories.site_content.db_conn', connection_context(listed)):
        page = repository.list_content(site_id='site-a', limit=1, cursor=content_id)
    assert page['items'][0]['slug'] == 'about'
    assert page['nextCursor'] == str(content_id)
    sql, params = listed.cursor_instance.executions[0]
    assert "site_id=%s AND state='published'" in sql
    assert params[0] == 'site-a'
    assert listed.tenant_ids == ['site-a']

    filtered = FakeConnection([content_row])
    with patch('api.repositories.site_content.db_conn', connection_context(filtered)):
        repository.list_content(
            site_id='site-a', limit=25, cursor=None, content_type='blog-post'
        )
    filtered_sql, filtered_params = filtered.cursor_instance.executions[0]
    assert 'content_type=%s' in filtered_sql
    assert filtered_params == ('site-a', 'blog-post', 26)

    found = FakeConnection([content_row])
    with patch('api.repositories.site_content.db_conn', connection_context(found)):
        item = repository.get_content(site_id='site-a', content_type='page', slug='about')
    assert item['id'] == content_id
    assert found.cursor_instance.executions[0][1] == ('site-a', 'page', 'about')

    missing = FakeConnection([])
    with patch('api.repositories.site_content.db_conn', connection_context(missing)):
        assert repository.get_content(site_id='site-a', content_type='page', slug='missing') is None

    media_row = (content_id, 'photo.png', 'image/png', 128, 'a' * 64, 'Owner', {}, now)
    media = FakeConnection([media_row])
    with patch('api.repositories.site_content.db_conn', connection_context(media)):
        asset = repository.get_media(site_id='site-a', asset_id=content_id)
    assert asset['mediaType'] == 'image/png'
    assert media.cursor_instance.executions[0][1] == ('site-a', str(content_id))

    no_media = FakeConnection([])
    with patch('api.repositories.site_content.db_conn', connection_context(no_media)):
        assert repository.get_media(site_id='site-a', asset_id=content_id) is None


def test_repository_search_enforces_public_published_join_and_freshness():
    now = datetime.now(UTC)
    document_id = UUID('33333333-3333-4333-8333-333333333333')
    row = (document_id, 'Notes', 'A' * 400, '/notes', now, now)
    connection = FakeConnection([row, row])
    repository = PostgresSiteContentRepository()
    with patch('api.repositories.site_content.db_conn', connection_context(connection)):
        page = repository.search(site_id='site-a', query='notes', limit=1, cursor=document_id)
    assert page['items'][0]['excerpt'] == 'A' * 320
    assert page['nextCursor'] == str(document_id)
    assert page['freshThrough'] == now
    sql, params = connection.cursor_instance.executions[0]
    assert 'c.id=d.content_id AND c.site_id=d.site_id' in sql
    assert "d.visibility='public'" in sql
    assert "c.state='published'" in sql
    assert params[0] == 'site-a'

    empty = FakeConnection([])
    with patch('api.repositories.site_content.db_conn', connection_context(empty)):
        empty_page = repository.search(site_id='site-a', query='none', limit=5, cursor=None)
    assert empty_page['items'] == []
    assert empty_page['nextCursor'] is None


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
