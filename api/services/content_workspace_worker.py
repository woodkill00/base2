from __future__ import annotations

import hashlib
import json
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
