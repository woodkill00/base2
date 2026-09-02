from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from api.db import db_conn
from api.security.content_workspace import canonical_digest
from api.services.content_workspace_derivative import generate_safe_derivative
from api.services.content_workspace_scanner import scan_content
from api.services.content_workspace_transfer import MAX_BYTES as MAX_TRANSFER_BYTES
from api.services.content_workspace_transfer import MAX_ROWS, export_csv


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
            'public' if state == 'published' and search_visible and not tombstoned else 'private'
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


def due_media_scans(*, limit: int = 10) -> list[tuple[str, str]]:
    if not 1 <= limit <= 50:
        raise ValueError('content_limit_exceeded')
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT site_id, id FROM sitecontent_mediaasset
               WHERE status='quarantined'
                 AND metadata->>'admission'='content_verified'
                 AND COALESCE(metadata->>'scanStatus','') NOT IN ('clean','infected')
               ORDER BY updated_at, id LIMIT %s""",
            (limit,),
        )
        return [(row[0], str(row[1])) for row in cur.fetchall()]


def scan_workspace_asset(
    *,
    site_id: str,
    asset_id: UUID,
    artifact_store,
    scanner=scan_content,
    derivative_builder=generate_safe_derivative,
) -> str:
    """Scan an exact encrypted object and promote only a stored safe derivative."""
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT storage_key, sha256, status, metadata, media_type
                       FROM sitecontent_mediaasset
                       WHERE id=%s AND site_id=%s FOR UPDATE""",
                    (str(asset_id), site_id),
                )
                row = cur.fetchone()
                if not row:
                    return 'not_found'
                if row[2] in {'validated', 'rejected', 'deleted'}:
                    return f'already_{row[2]}'
                if row[2] != 'quarantined':
                    return 'not_ready'
                metadata = row[3] if isinstance(row[3], dict) else {}
                if metadata.get('scanStatus') == 'clean':
                    return 'already_scanned'
                content = artifact_store.get(row[0], expected_sha256=row[1])
                verdict = scanner(content)
                if verdict not in {'clean', 'infected'}:
                    raise ValueError('content_scanner_response_invalid')
                next_status = 'rejected'
                derivative = None
                stored_derivative = None
                if verdict == 'clean':
                    derivative = derivative_builder(content=content, media_type=row[4])
                    stored_derivative = artifact_store.put(
                        namespace='variants',
                        site_id=site_id,
                        object_id=f'{asset_id}-safe',
                        content=derivative.content,
                    )
                    if stored_derivative.sha256 != derivative.sha256:
                        raise ValueError('content_integrity_failed')
                    next_status = 'validated'
                safe_metadata = {
                    'admission': 'content_verified',
                    'scanStatus': verdict,
                    'scannerRef': 'clamav:instream',
                }
                for key in ('width', 'height'):
                    if isinstance(metadata.get(key), int):
                        safe_metadata[key] = metadata[key]
                if stored_derivative is not None:
                    safe_metadata['derivativeSha256'] = stored_derivative.sha256
                    cur.execute(
                        """INSERT INTO sitecontent_mediavariant
                           (id, asset_id, name, storage_key, media_type, byte_size,
                            sha256, width, height, created_at)
                           VALUES (%s,%s,'safe',%s,%s,%s,%s,%s,%s,NOW())
                           ON CONFLICT (asset_id, name) DO NOTHING""",
                        (
                            str(uuid4()),
                            str(asset_id),
                            stored_derivative.object_key,
                            derivative.media_type,
                            stored_derivative.byte_size,
                            stored_derivative.sha256,
                            derivative.width,
                            derivative.height,
                        ),
                    )
                cur.execute(
                    """UPDATE sitecontent_mediaasset SET status=%s, metadata=%s::jsonb,
                           updated_at=NOW()
                       WHERE id=%s AND site_id=%s AND status='quarantined'""",
                    (next_status, json.dumps(safe_metadata), str(asset_id), site_id),
                )
                cur.execute(
                    """INSERT INTO sitecontent_workspaceauditevent
                       (id, site_id, actor_ref, object_type, object_ref, action, outcome,
                        correlation_id, metadata, created_at)
                       VALUES (%s,%s,'system:media-scanner','media_asset',%s,
                               'content.asset_scan',%s,'',%s::jsonb,NOW())""",
                    (
                        str(uuid4()),
                        site_id,
                        str(asset_id),
                        'accepted' if verdict == 'clean' else 'rejected',
                        json.dumps({'status': verdict, 'sha256': row[1]}),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return 'validated_safe_derivative' if verdict == 'clean' else 'scanned_infected'


def due_export_jobs(*, limit: int = 10) -> list[tuple[str, str]]:
    if not 1 <= limit <= 50:
        raise ValueError('content_limit_exceeded')
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT site_id, id FROM sitecontent_exportjob
               WHERE status='queued' AND expires_at>NOW()
               ORDER BY created_at, id LIMIT %s""",
            (limit,),
        )
        return [(row[0], str(row[1])) for row in cur.fetchall()]


def _export_payload(rows: list[dict[str, Any]], fields: list[str], output_format: str) -> bytes:
    projected = [{field: row.get(field) for field in fields} for row in rows]
    if output_format == 'json':
        return json.dumps(
            projected, sort_keys=True, separators=(',', ':'), ensure_ascii=False
        ).encode()
    if output_format == 'csv':
        normalized = [
            {
                field: (
                    json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                    if isinstance(value, (dict, list))
                    else value
                )
                for field, value in row.items()
            }
            for row in projected
        ]
        return export_csv(normalized, fields)
    raise ValueError('content_schema_invalid')


def process_export_job(*, site_id: str, job_id: UUID, artifact_store) -> str:
    """Create one bounded permission-snapshot export and retain it encrypted at rest."""
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT j.status, j.schema_version, j.format, j.projection_digest,
                              j.projection_fields, j.requester_ref, d.type_key,
                              j.output_sha256, j.encrypted_object_key
                       FROM sitecontent_exportjob j
                       JOIN sitecontent_contenttypedefinition d ON d.id=j.definition_id
                       WHERE j.id=%s AND j.site_id=%s AND d.site_id=%s FOR UPDATE""",
                    (str(job_id), site_id, site_id),
                )
                row = cur.fetchone()
                if not row:
                    return 'not_found'
                if row[0] == 'completed':
                    return 'already_completed'
                if row[0] != 'queued':
                    return 'not_ready'
                fields = row[4] if isinstance(row[4], list) else []
                if (
                    not fields
                    or len(fields) > 64
                    or len(fields) != len(set(fields))
                    or canonical_digest(
                        {
                            'site': site_id,
                            'type': row[6],
                            'schema': row[1],
                            'requester': row[5],
                            'fields': fields,
                        }
                    )
                    != row[3]
                ):
                    raise ValueError('content_integrity_failed')
                cur.execute(
                    """SELECT values FROM sitecontent_contentrecord
                       WHERE site_id=%s AND content_type=%s AND deleted_at IS NULL
                       ORDER BY slug, id LIMIT %s""",
                    (site_id, row[6], MAX_ROWS + 1),
                )
                records = cur.fetchall()
                if len(records) > MAX_ROWS:
                    raise ValueError('content_limit_exceeded')
                values = [item[0] if isinstance(item[0], dict) else {} for item in records]
                content = _export_payload(values, fields, row[2])
                if not content or len(content) > MAX_TRANSFER_BYTES:
                    raise ValueError('content_limit_exceeded')
                stored = artifact_store.put(
                    namespace='exports',
                    site_id=site_id,
                    object_id=str(job_id),
                    content=content,
                )
                cur.execute(
                    """UPDATE sitecontent_exportjob
                       SET status='completed', output_sha256=%s, encrypted_object_key=%s,
                           counters=%s::jsonb, completed_at=NOW(), updated_at=NOW()
                       WHERE id=%s AND site_id=%s AND status='queued' RETURNING id""",
                    (
                        stored.sha256,
                        stored.object_key,
                        json.dumps({'total': len(values)}),
                        str(job_id),
                        site_id,
                    ),
                )
                if not cur.fetchone():
                    raise ValueError('content_job_transition_invalid')
                cur.execute(
                    """INSERT INTO sitecontent_workspaceauditevent
                       (id, site_id, actor_ref, object_type, object_ref, action, outcome,
                        correlation_id, metadata, created_at)
                       VALUES (%s,%s,'system:export-worker','export_job',%s,
                               'content.export_complete','accepted','',%s::jsonb,NOW())""",
                    (
                        str(uuid4()),
                        site_id,
                        str(job_id),
                        json.dumps({'count': len(values), 'sha256': stored.sha256}),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return 'completed'
