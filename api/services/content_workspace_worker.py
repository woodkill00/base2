from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from api.db import db_conn


def due_publication_ids(*, limit: int = 25) -> list[tuple[str, str]]:
    if not 1 <= limit <= 100:
        raise ValueError('content_limit_exceeded')
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT site_id, id FROM sitecontent_contentrecord
               WHERE state='scheduled' AND publish_at<=NOW() AND deleted_at IS NULL
               ORDER BY publish_at, id LIMIT %s""",
            (limit,),
        )
        return [(row[0], str(row[1])) for row in cur.fetchall()]


def publish_scheduled_record(*, site_id: str, record_id: UUID) -> str:
    """Publish one due record exactly once; replay is a bounded no-op."""
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, version, schema_version, values, state, publish_at
                       FROM sitecontent_contentrecord
                       WHERE id=%s AND site_id=%s FOR UPDATE""",
                    (str(record_id), site_id),
                )
                row = cur.fetchone()
                if not row:
                    return 'not_found'
                if row[4] == 'published':
                    return 'already_published'
                if row[4] != 'scheduled' or row[5] is None:
                    return 'not_due'
                cur.execute('SELECT %s<=NOW()', (row[5],))
                if not cur.fetchone()[0]:
                    return 'not_due'
                snapshot = json.dumps(row[3], sort_keys=True, separators=(',', ':'))
                cur.execute(
                    """INSERT INTO sitecontent_contentrevision
                       (id, content_id, revision, snapshot, actor_ref, created_at,
                        schema_version, snapshot_sha256, action, restored_from_version)
                       VALUES (%s,%s,%s,%s::jsonb,'system:scheduler',NOW(),%s,%s,'publish',NULL)""",
                    (
                        str(uuid4()),
                        str(record_id),
                        row[1],
                        snapshot,
                        row[2],
                        hashlib.sha256(snapshot.encode()).hexdigest(),
                    ),
                )
                cur.execute(
                    """UPDATE sitecontent_contentrecord SET state='published', publish_at=NULL,
                       schedule_timezone='',
                       published_at=NOW(), version=version+1, updated_at=NOW()
                       WHERE id=%s AND site_id=%s AND state='scheduled'""",
                    (str(record_id), site_id),
                )
                cur.execute(
                    """INSERT INTO sitecontent_workspaceauditevent
                       (id, site_id, actor_ref, object_type, object_ref, action, outcome,
                        correlation_id, metadata, created_at)
                       VALUES (%s,%s,'system:scheduler','content_record',%s,
                               'content.publish_scheduled','accepted','',%s::jsonb,NOW())""",
                    (str(uuid4()), site_id, str(record_id), '{}'),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return 'published'


def due_index_records(*, limit: int = 25) -> list[tuple[str, str, int]]:
    """Discover records whose durable search projection is absent or stale."""
    if not 1 <= limit <= 100:
        raise ValueError('content_limit_exceeded')
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT c.site_id, c.id, c.version
               FROM sitecontent_contentrecord c
               LEFT JOIN sitecontent_searchdocument d
                 ON d.content_id=c.id AND d.site_id=c.site_id
               WHERE d.id IS NULL OR d.source_updated_at<c.updated_at
                  OR (c.deleted_at IS NOT NULL AND d.tombstoned_at IS NULL)
               ORDER BY c.updated_at, c.id LIMIT %s""",
            (limit,),
        )
        return [(row[0], str(row[1]), int(row[2])) for row in cur.fetchall()]


def build_search_projection(
    *,
    content_type: str,
    slug: str,
    title: str,
    body: str,
    state: str,
    search_visible: bool,
    updated_at: datetime,
    deleted_at: datetime | None,
) -> dict[str, Any]:
    """Build the closed public-search projection; dynamic record values stay private."""
    tombstoned = deleted_at is not None or state == 'deleted'
    return {
        'title': title,
        'body': body,
        'url_path': f'/{content_type}/{slug}',
        'visibility': (
            'public'
            if state == 'published' and search_visible and not tombstoned
            else 'private'
        ),
        'source_updated_at': updated_at,
        'tombstoned': tombstoned,
    }


def index_workspace_record(*, site_id: str, record_id: UUID, job_version: int) -> str:
    """Converge one version-bound indexing job without letting stale work overwrite data."""
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, content_type, slug, title, body, state, search_visible,
                              updated_at, deleted_at, version
                       FROM sitecontent_contentrecord
                       WHERE id=%s AND site_id=%s FOR UPDATE""",
                    (str(record_id), site_id),
                )
                row = cur.fetchone()
                if not row:
                    return 'not_found'
                current_version = int(row[9])
                if job_version < current_version:
                    return 'stale_job'
                if job_version > current_version:
                    raise ValueError('content_index_version_invalid')
                projection = build_search_projection(
                    content_type=row[1],
                    slug=row[2],
                    title=row[3],
                    body=row[4],
                    state=row[5],
                    search_visible=bool(row[6]),
                    updated_at=row[7],
                    deleted_at=row[8],
                )
                cur.execute(
                    """SELECT source_updated_at FROM sitecontent_searchdocument
                       WHERE content_id=%s AND site_id=%s""",
                    (str(record_id), site_id),
                )
                existing = cur.fetchone()
                if existing and existing[0] >= projection['source_updated_at']:
                    return 'current'
                cur.execute(
                    """INSERT INTO sitecontent_searchdocument
                       (id, site_id, content_id, title, body, url_path, visibility,
                        source_updated_at, indexed_at, tombstoned_at, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),
                               CASE WHEN %s THEN NOW() ELSE NULL END,NOW(),NOW())
                       ON CONFLICT (content_id) DO UPDATE SET
                         title=EXCLUDED.title, body=EXCLUDED.body,
                         url_path=EXCLUDED.url_path, visibility=EXCLUDED.visibility,
                         source_updated_at=EXCLUDED.source_updated_at,
                         indexed_at=NOW(), tombstoned_at=EXCLUDED.tombstoned_at,
                         updated_at=NOW()
                       WHERE sitecontent_searchdocument.site_id=EXCLUDED.site_id
                         AND sitecontent_searchdocument.source_updated_at<EXCLUDED.source_updated_at""",
                    (
                        str(uuid4()),
                        site_id,
                        str(record_id),
                        projection['title'],
                        projection['body'],
                        projection['url_path'],
                        projection['visibility'],
                        projection['source_updated_at'],
                        projection['tombstoned'],
                    ),
                )
                cur.execute(
                    """INSERT INTO sitecontent_workspaceauditevent
                       (id, site_id, actor_ref, object_type, object_ref, action, outcome,
                        correlation_id, metadata, created_at)
                       VALUES (%s,%s,'system:indexer','content_record',%s,
                               'content.search_index','accepted','',%s::jsonb,NOW())""",
                    (
                        str(uuid4()),
                        site_id,
                        str(record_id),
                        json.dumps({'version': current_version}),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return 'indexed'
