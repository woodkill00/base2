"""Closed supported-pack routing and projection-only legacy correction contracts."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from api.services import content_workspace_worker as worker
from api.tests.test_content_workspace_worker import Connection, Cursor, bind

PACKS = [
    ('blog-post', 'blog', '/blog'),
    ('doc-page', 'documentation', '/docs'),
    ('portfolio-item', 'portfolio', '/portfolio'),
]
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('type_key,module_id,path', PACKS)
def test_projection_matches_real_pack_manifest_and_detail_route(type_key, module_id, path):
    manifest = json.loads((ROOT / 'modules' / module_id / 'module.json').read_text())
    assert f'/api/content/{type_key}/{{slug}}' in manifest['apiRoutes']
    assert f'{path}/{{slug}}' in manifest['uiRoutes']
    routes = (ROOT / 'react-app/src/routes/PublicRoutes.jsx').read_text()
    assert re.search(
        rf'path="{path}/:slug"\s+element=\{{\s*<PackDetailRoute '
        rf'moduleId="{module_id}" title="[^"]+" contentType="{type_key}"',
        routes,
    )
    projection = worker.build_search_projection(
        content_type=type_key,
        slug='entry',
        title='Title',
        body='Body',
        state='published',
        search_visible=True,
        updated_at=datetime(2026, 9, 2, tzinfo=UTC),
        deleted_at=None,
    )
    assert projection['url_path'] == f'{path}/entry'


def test_discovery_includes_only_equal_time_live_exact_supported_legacy_paths(monkeypatch):
    cursor = Cursor([])
    bind(monkeypatch, Connection(cursor))
    worker.due_index_records()
    sql, params = cursor.calls[0]
    assert 'd.source_updated_at=c.updated_at' in sql
    assert "d.url_path='/' || c.content_type || '/' || c.slug" in sql
    assert 'd.tombstoned_at IS NULL' in sql
    assert 'c.deleted_at IS NULL' in sql
    assert params == (['blog-post', 'doc-page', 'portfolio-item'], 25)


@pytest.mark.parametrize('changed', [True, False])
def test_equal_version_repair_is_atomic_url_only_and_tenant_scoped(monkeypatch, changed):
    timestamp = datetime(2026, 9, 2, tzinfo=UTC)
    row = (
        UUID(int=106),
        'blog-post',
        'entry',
        'Title',
        'Body',
        'published',
        True,
        timestamp,
        None,
        7,
    )
    cursor = Cursor([row, (timestamp,), (UUID(int=1),) if changed else None])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)
    result = worker.index_workspace_record(site_id='site-a', record_id=row[0], job_version=7)
    assert result == ('indexed' if changed else 'current')
    update, params = next(call for call in cursor.calls if call[0].startswith('UPDATE'))
    assert update.startswith('UPDATE sitecontent_searchdocument SET url_path=%s WHERE')
    assert 'source_updated_at=%s' in update and 'url_path=%s' in update
    assert 'tombstoned_at IS NULL' in update and 'RETURNING id' in update
    assert params == ('/blog/entry', str(row[0]), 'site-a', timestamp, '/blog-post/entry')
    assert scopes == ['site-a']
    assert connection.commits == int(changed)
    assert not any('INSERT INTO sitecontent_searchdocument' in sql for sql, _ in cursor.calls)


@pytest.mark.parametrize(
    'type_key,deleted,state,newer',
    [
        ('article', False, 'published', False),
        ('blog-post', True, 'published', False),
        ('blog-post', False, 'deleted', False),
        ('blog-post', False, 'published', True),
    ],
)
def test_current_projection_guards_never_attempt_repair(
    monkeypatch, type_key, deleted, state, newer
):
    from datetime import timedelta

    timestamp = datetime(2026, 9, 2, tzinfo=UTC)
    row = (
        UUID(int=106),
        type_key,
        'entry',
        'Title',
        'Body',
        state,
        True,
        timestamp,
        timestamp if deleted else None,
        7,
    )
    cursor = Cursor([row, (timestamp + timedelta(seconds=int(newer)),)])
    connection = Connection(cursor)
    bind(monkeypatch, connection)
    assert (
        worker.index_workspace_record(site_id='site-a', record_id=row[0], job_version=7)
        == 'current'
    )
    assert not any(sql.startswith('UPDATE') for sql, _ in cursor.calls)
    assert connection.commits == 0
