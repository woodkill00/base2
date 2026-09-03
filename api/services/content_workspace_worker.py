from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from api.db import workspace_worker_db_conn as db_conn
from api.repositories.content_workspace import _validate_values
from api.security.content_workspace import canonical_digest
from api.services.content_workspace_derivative import generate_safe_derivative
from api.services.content_workspace_scanner import scan_content
from api.services.content_workspace_transfer import MAX_BYTES as MAX_TRANSFER_BYTES
from api.services.content_workspace_transfer import (
    MAX_ROWS,
    ImportOutcome,
    ParsedRows,
    export_csv,
    parse_csv,
    parse_json,
    plan_import,
)


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


def workspace_health_summary(*, site_id: str) -> dict[str, Any]:
    """Return bounded operational evidence without submitted content or object locations."""
    with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT kind, status, error_code, count(*),
                      COALESCE(MAX(duration_seconds), 0)
               FROM (
                 SELECT 'import' AS kind, status, error_code,
                        EXTRACT(EPOCH FROM (updated_at-created_at)) AS duration_seconds
                 FROM sitecontent_importjob WHERE site_id=%s
                 UNION ALL
                 SELECT 'export' AS kind, status, error_code,
                        EXTRACT(EPOCH FROM (updated_at-created_at)) AS duration_seconds
                 FROM sitecontent_exportjob WHERE site_id=%s
               ) jobs
               GROUP BY kind, status, error_code
               ORDER BY kind, status, error_code LIMIT 100""",
            (site_id, site_id),
        )
        rows = cur.fetchall()
    outcomes = []
    for kind, state, error_code, count, duration in rows:
        safe_error = (
            error_code
            if re.fullmatch(r'content_[a-z0-9_]{3,55}', error_code or '')
            else 'content_dependency_unavailable'
            if error_code
            else ''
        )
        outcomes.append(
            {
                'kind': kind if kind in {'import', 'export'} else 'unknown',
                'state': state
                if state
                in {
                    'uploaded',
                    'validated',
                    'review_required',
                    'committing',
                    'queued',
                    'running',
                    'completed',
                    'failed',
                    'cancelled',
                    'expired',
                }
                else 'unknown',
                'errorCode': safe_error,
                'count': min(max(int(count), 0), 1_000_000),
                'maximumDurationSeconds': min(max(float(duration), 0.0), 31_536_000.0),
            }
        )
    payload = {
        'schemaVersion': 1,
        'siteRef': hashlib.sha256(site_id.encode()).hexdigest()[:16],
        'outcomes': outcomes,
    }
    payload['digest'] = canonical_digest(payload)
    return payload


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
                if stored_derivative is not None and derivative is not None:
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


def mark_export_failed(*, site_id: str, job_id: UUID, error_code: str) -> bool:
    safe_code = (
        error_code
        if re.fullmatch(r'content_[a-z0-9_]{3,55}', error_code or '')
        else 'content_dependency_unavailable'
    )
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE sitecontent_exportjob
                       SET status='failed', error_code=%s, completed_at=NOW(), updated_at=NOW()
                       WHERE id=%s AND site_id=%s AND status IN ('queued','running')
                       RETURNING id""",
                    (safe_code, str(job_id), site_id),
                )
                changed = bool(cur.fetchone())
                if changed:
                    cur.execute(
                        """INSERT INTO sitecontent_workspaceauditevent
                           (id, site_id, actor_ref, object_type, object_ref, action, outcome,
                            correlation_id, metadata, created_at)
                           VALUES (%s,%s,'system:export-worker','export_job',%s,
                                   'content.export_failed','rejected','',%s::jsonb,NOW())""",
                        (
                            str(uuid4()),
                            site_id,
                            str(job_id),
                            json.dumps({'errorCode': safe_code}),
                        ),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return changed


def expire_export_jobs(*, artifact_store, limit: int = 100) -> int:
    if not 1 <= limit <= 500:
        raise ValueError('content_limit_exceeded')
    with db_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, site_id, encrypted_object_key, output_sha256
                       FROM sitecontent_exportjob
                       WHERE status<>'expired' AND expires_at<=NOW()
                       ORDER BY expires_at, id LIMIT %s FOR UPDATE SKIP LOCKED""",
                    (limit,),
                )
                rows = cur.fetchall()
                for job_id, site_id, object_key, output_sha256 in rows:
                    if object_key:
                        artifact_store.delete(
                            namespace='exports', site_id=site_id, object_id=str(job_id),
                            object_key=object_key, expected_sha256=output_sha256,
                            missing_ok=True,
                        )
                    cur.execute(
                        """UPDATE sitecontent_exportjob
                           SET status='expired', encrypted_object_key='', output_sha256='',
                               completed_at=NOW(), error_code='content_export_expired',
                               updated_at=NOW()
                           WHERE id=%s AND site_id=%s AND status<>'expired'""",
                        (str(job_id), site_id),
                    )
                expired = len(rows)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return expired


def purge_workspace_retention(*, artifact_store, recovery_days: int = 30, limit: int = 100):
    """Purge only unreferenced, expired exact-owned workspace objects and tombstones."""
    if not 1 <= recovery_days <= 365 or not 1 <= limit <= 500:
        raise ValueError('content_limit_exceeded')
    result = {'assets': 0, 'records': 0}
    with db_conn() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT a.id, a.site_id, a.storage_key, a.sha256
                       FROM sitecontent_mediaasset a
                       WHERE a.status='deleted' AND a.retention_until<=NOW()
                         AND NOT EXISTS (
                           SELECT 1 FROM sitecontent_assetbinding b WHERE b.asset_id=a.id
                         )
                       ORDER BY a.retention_until, a.id
                       LIMIT %s FOR UPDATE OF a SKIP LOCKED""",
                    (limit,),
                )
                assets = cur.fetchall()
                for asset_id, site_id, storage_key, sha256 in assets:
                    cur.execute(
                        """SELECT name, storage_key, sha256
                           FROM sitecontent_mediavariant WHERE asset_id=%s ORDER BY name""",
                        (str(asset_id),),
                    )
                    variants = cur.fetchall()
                    for name, variant_key, variant_sha256 in variants:
                        artifact_store.delete(
                            namespace='variants', site_id=site_id,
                            object_id=f'{asset_id}-{name}', object_key=variant_key,
                            expected_sha256=variant_sha256, missing_ok=True,
                        )
                    artifact_store.delete(
                        namespace='media', site_id=site_id, object_id=str(asset_id),
                        object_key=storage_key, expected_sha256=sha256, missing_ok=True,
                    )
                    cur.execute(
                        """INSERT INTO sitecontent_workspaceauditevent
                           (id,site_id,actor_ref,object_type,object_ref,action,outcome,
                            correlation_id,metadata,created_at)
                           VALUES (%s,%s,'system:retention','media_asset',%s,
                                   'content.asset_hard_delete','accepted','',%s::jsonb,NOW())""",
                        (str(uuid4()), site_id, str(asset_id), json.dumps({'count': 1})),
                    )
                    cur.execute(
                        "DELETE FROM sitecontent_mediaasset WHERE id=%s AND site_id=%s",
                        (str(asset_id), site_id),
                    )
                    result['assets'] += cur.rowcount

                cur.execute(
                    """SELECT r.id, r.site_id FROM sitecontent_contentrecord r
                       WHERE r.state='deleted' AND r.deleted_at<=NOW()-(%s*INTERVAL '1 day')
                         AND NOT EXISTS (
                           SELECT 1 FROM sitecontent_contentrelationship rel
                           WHERE rel.source_id=r.id OR rel.target_id=r.id
                         )
                         AND NOT EXISTS (
                           SELECT 1 FROM sitecontent_assetbinding b WHERE b.record_id=r.id
                         )
                       ORDER BY r.deleted_at, r.id
                       LIMIT %s FOR UPDATE OF r SKIP LOCKED""",
                    (recovery_days, limit),
                )
                records = cur.fetchall()
                for record_id, site_id in records:
                    cur.execute(
                        """INSERT INTO sitecontent_workspaceauditevent
                           (id,site_id,actor_ref,object_type,object_ref,action,outcome,
                            correlation_id,metadata,created_at)
                           VALUES (%s,%s,'system:retention','content_record',%s,
                                   'content.record_hard_delete','accepted','',%s::jsonb,NOW())""",
                        (str(uuid4()), site_id, str(record_id), json.dumps({'count': 1})),
                    )
                    cur.execute(
                        "DELETE FROM sitecontent_contentrecord WHERE id=%s AND site_id=%s",
                        (str(record_id), site_id),
                    )
                    result['records'] += cur.rowcount
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return result


def due_import_validations(*, limit: int = 10) -> list[tuple[str, str]]:
    if not 1 <= limit <= 50:
        raise ValueError('content_limit_exceeded')
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT site_id, id FROM sitecontent_importjob
               WHERE status='uploaded' AND source_object_key<>''
               ORDER BY updated_at, id LIMIT %s""",
            (limit,),
        )
        return [(row[0], str(row[1])) for row in cur.fetchall()]


def mark_import_failed(*, site_id: str, job_id: UUID, error_code: str) -> bool:
    """Close a worker-owned import without persisting exception text."""
    safe_code = (
        error_code
        if re.fullmatch(r'content_[a-z0-9_]{3,55}', error_code or '')
        else 'content_dependency_unavailable'
    )
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE sitecontent_importjob
                       SET status='failed', error_code=%s, completed_at=NOW(), updated_at=NOW()
                       WHERE id=%s AND site_id=%s
                         AND status IN ('uploaded','validated','committing')
                       RETURNING id""",
                    (safe_code, str(job_id), site_id),
                )
                changed = bool(cur.fetchone())
                if changed:
                    cur.execute(
                        """INSERT INTO sitecontent_workspaceauditevent
                           (id, site_id, actor_ref, object_type, object_ref, action, outcome,
                            correlation_id, metadata, created_at)
                           VALUES (%s,%s,'system:import-worker','import_job',%s,
                                   'content.import_failed','rejected','',%s::jsonb,NOW())""",
                        (
                            str(uuid4()),
                            site_id,
                            str(job_id),
                            json.dumps({'errorCode': safe_code}),
                        ),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return changed


def _mapped_import_rows(parsed: ParsedRows, mapping: dict, fields: list[tuple]):
    allowed = {row[0] for row in fields}
    valid_rows: list[dict[str, Any]] = []
    ordinals: list[int] = []
    rejected: list[ImportOutcome] = []
    for ordinal, source in enumerate(parsed.rows, start=1):
        mapped: dict[str, Any] = {}
        invalid = False
        for source_key, value in source.items():
            target = mapping.get(source_key, source_key)
            if target in mapped or target not in allowed | {'slug', 'title'}:
                invalid = True
                break
            mapped[target] = value
        values = {key: value for key, value in mapped.items() if key in allowed}
        try:
            if (
                invalid
                or not isinstance(mapped.get('slug'), str)
                or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', mapped['slug'])
                or not isinstance(mapped.get('title'), str)
                or not 1 <= len(mapped['title']) <= 300
            ):
                raise ValueError('content_schema_invalid')
            _validate_values(values, fields)
        except (TypeError, ValueError):
            rejected.append(
                ImportOutcome(
                    ordinal=ordinal,
                    source_row_sha256=hashlib.sha256(
                        json.dumps(
                            source,
                            sort_keys=True,
                            separators=(',', ':'),
                            ensure_ascii=False,
                        ).encode()
                    ).hexdigest(),
                    action='reject',
                )
            )
            continue
        valid_rows.append({'slug': mapped['slug'], 'title': mapped['title'], **values})
        ordinals.append(ordinal)
    return valid_rows, ordinals, rejected


def validate_import_job(*, site_id: str, job_id: UUID, artifact_store) -> str:
    """Parse and stage row outcomes without mutating content records."""
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT j.status, j.schema_version, j.source_sha256, j.source_format,
                              j.source_object_key, j.mapping, j.duplicate_policy,
                              j.atomic_policy, d.type_key, j.definition_id
                       FROM sitecontent_importjob j
                       JOIN sitecontent_contenttypedefinition d ON d.id=j.definition_id
                       WHERE j.id=%s AND j.site_id=%s AND d.site_id=%s FOR UPDATE""",
                    (str(job_id), site_id, site_id),
                )
                row = cur.fetchone()
                if not row:
                    return 'not_found'
                if row[0] in {'validated', 'review_required'}:
                    return 'already_validated'
                if row[0] != 'uploaded' or not row[4]:
                    return 'not_ready'
                content = artifact_store.get(row[4], expected_sha256=row[2])
                parsed = parse_json(content) if row[3] == 'json' else parse_csv(content)
                cur.execute(
                    """SELECT field_key, field_kind, required, nullable, default_value, validation
                       FROM sitecontent_contentfielddefinition
                       WHERE definition_id=%s ORDER BY "order", field_key""",
                    (str(row[9]),),
                )
                fields = cur.fetchall()
                mapping = row[5] if isinstance(row[5], dict) else {}
                valid_rows, ordinals, rejected = _mapped_import_rows(parsed, mapping, fields)
                cur.execute(
                    """SELECT id, slug, title, values FROM sitecontent_contentrecord
                       WHERE site_id=%s AND content_type=%s AND deleted_at IS NULL
                       ORDER BY slug, id LIMIT %s""",
                    (site_id, row[8], MAX_ROWS + 1),
                )
                existing_rows = cur.fetchall()
                if len(existing_rows) > MAX_ROWS:
                    raise ValueError('content_limit_exceeded')
                existing = [
                    {'id': str(item[0]), 'slug': item[1], 'title': item[2], **(item[3] or {})}
                    for item in existing_rows
                ]
                plan = plan_import(
                    ParsedRows(tuple(valid_rows), parsed.sha256),
                    existing=existing,
                    exact_fields=['slug'],
                    similarity_fields=['title'],
                )
                outcomes = [
                    ImportOutcome(
                        ordinal=ordinals[item.ordinal - 1],
                        source_row_sha256=item.source_row_sha256,
                        action=(
                            'skip'
                            if item.action == 'update' and row[6] == 'skip_exact'
                            else 'review'
                            if item.action == 'update' and row[6] == 'review'
                            else item.action
                        ),
                        exact_match_id=item.exact_match_id,
                        candidate_ids=(
                            (item.exact_match_id,)
                            if item.action == 'update'
                            and row[6] == 'review'
                            and item.exact_match_id
                            else item.candidate_ids
                        ),
                    )
                    for item in plan.outcomes
                ] + rejected
                outcomes.sort(key=lambda item: item.ordinal)
                for item in outcomes:
                    issues = (
                        [{'field': 'row', 'code': 'schema_invalid'}]
                        if item.action == 'reject'
                        else []
                    )
                    cur.execute(
                        """INSERT INTO sitecontent_importrowoutcome
                           (id, site_id, job_id, ordinal, source_row_sha256, proposed_action,
                            field_issues, exact_match_id, candidate_ids, result_record_id,
                            result_version, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,NULL,NULL,NOW(),NOW())
                           ON CONFLICT (job_id, ordinal) DO NOTHING""",
                        (
                            str(uuid4()),
                            site_id,
                            str(job_id),
                            item.ordinal,
                            item.source_row_sha256,
                            item.action,
                            json.dumps(issues),
                            item.exact_match_id,
                            json.dumps(list(item.candidate_ids)),
                        ),
                    )
                counters = {
                    'total': len(parsed.rows),
                    'valid': len(valid_rows),
                    'invalid': len(rejected),
                    'created': sum(item.action == 'create' for item in outcomes),
                    'updated': sum(item.action == 'update' for item in outcomes),
                    'skipped': sum(item.action == 'skip' for item in outcomes),
                    'review': sum(item.action == 'review' for item in outcomes),
                }
                next_status = 'review_required' if rejected or counters['review'] else 'validated'
                cur.execute(
                    """UPDATE sitecontent_importjob SET status=%s, counters=%s::jsonb,
                              error_code='', updated_at=NOW()
                       WHERE id=%s AND site_id=%s AND status='uploaded' RETURNING id""",
                    (next_status, json.dumps(counters), str(job_id), site_id),
                )
                if not cur.fetchone():
                    raise ValueError('content_job_transition_invalid')
                cur.execute(
                    """INSERT INTO sitecontent_workspaceauditevent
                       (id, site_id, actor_ref, object_type, object_ref, action, outcome,
                        correlation_id, metadata, created_at)
                       VALUES (%s,%s,'system:import-worker','import_job',%s,
                               'content.import_validate','accepted','',%s::jsonb,NOW())""",
                    (
                        str(uuid4()),
                        site_id,
                        str(job_id),
                        json.dumps({'count': len(parsed.rows), 'status': next_status}),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return next_status


def due_import_commits(*, limit: int = 10) -> list[tuple[str, str]]:
    if not 1 <= limit <= 50:
        raise ValueError('content_limit_exceeded')
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT site_id, id FROM sitecontent_importjob
               WHERE status='committing' AND source_object_key<>''
               ORDER BY updated_at, id LIMIT %s""",
            (limit,),
        )
        return [(row[0], str(row[1])) for row in cur.fetchall()]


def process_import_commit(*, site_id: str, job_id: UUID, artifact_store) -> str:
    """Apply one fully reviewed import atomically and bind every resulting row."""
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT j.status, j.schema_version, j.source_sha256, j.source_format,
                              j.source_object_key, j.mapping, d.type_key, j.definition_id
                       FROM sitecontent_importjob j
                       JOIN sitecontent_contenttypedefinition d ON d.id=j.definition_id
                       WHERE j.id=%s AND j.site_id=%s AND d.site_id=%s FOR UPDATE""",
                    (str(job_id), site_id, site_id),
                )
                job = cur.fetchone()
                if not job:
                    return 'not_found'
                if job[0] == 'completed':
                    return 'already_completed'
                if job[0] != 'committing' or not job[4]:
                    return 'not_ready'
                content = artifact_store.get(job[4], expected_sha256=job[2])
                parsed = parse_json(content) if job[3] == 'json' else parse_csv(content)
                cur.execute(
                    """SELECT field_key, field_kind, required, nullable, default_value, validation
                       FROM sitecontent_contentfielddefinition
                       WHERE definition_id=%s ORDER BY "order", field_key""",
                    (str(job[7]),),
                )
                fields = cur.fetchall()
                valid_rows, ordinals, rejected = _mapped_import_rows(
                    parsed, job[5] if isinstance(job[5], dict) else {}, fields
                )
                if rejected or len(valid_rows) != len(parsed.rows):
                    raise ValueError('content_integrity_failed')
                rows_by_ordinal = dict(zip(ordinals, valid_rows, strict=True))
                cur.execute(
                    """SELECT ordinal, source_row_sha256, proposed_action, exact_match_id
                       FROM sitecontent_importrowoutcome
                       WHERE job_id=%s AND site_id=%s ORDER BY ordinal FOR UPDATE""",
                    (str(job_id), site_id),
                )
                outcomes = cur.fetchall()
                if len(outcomes) != len(parsed.rows):
                    raise ValueError('content_integrity_failed')
                allowed = {field[0] for field in fields}
                completed_counts = {'created': 0, 'updated': 0, 'skipped': 0}
                for ordinal, source_digest, action, exact_match_id in outcomes:
                    imported = rows_by_ordinal.get(int(ordinal))
                    if imported is None or action not in {'create', 'update', 'skip'}:
                        raise ValueError('content_integrity_failed')
                    calculated = hashlib.sha256(
                        json.dumps(
                            imported,
                            sort_keys=True,
                            separators=(',', ':'),
                            ensure_ascii=False,
                        ).encode()
                    ).hexdigest()
                    if calculated != source_digest:
                        raise ValueError('content_integrity_failed')
                    values = {key: value for key, value in imported.items() if key in allowed}
                    result_id = None
                    result_version = None
                    if action == 'create':
                        result_id = uuid4()
                        cur.execute(
                            """INSERT INTO sitecontent_contentrecord
                               (id, site_id, content_type, slug, title, excerpt, body, metadata,
                                state, publish_at, published_at, sitemap_include, search_visible,
                                version, definition_id, schema_version, values, deleted_at,
                                created_at, updated_at)
                               VALUES (%s,%s,%s,%s,%s,'','',%s::jsonb,'draft',NULL,NULL,TRUE,TRUE,
                                       1,%s,%s,%s::jsonb,NULL,NOW(),NOW())""",
                            (
                                str(result_id),
                                site_id,
                                job[6],
                                imported['slug'],
                                imported['title'],
                                '{}',
                                str(job[7]),
                                job[1],
                                json.dumps(values),
                            ),
                        )
                        result_version = 1
                        completed_counts['created'] += 1
                    elif action == 'update':
                        if exact_match_id is None:
                            raise ValueError('content_integrity_failed')
                        cur.execute(
                            """SELECT id, version, schema_version, values
                               FROM sitecontent_contentrecord
                               WHERE id=%s AND site_id=%s AND content_type=%s
                                 AND deleted_at IS NULL FOR UPDATE""",
                            (str(exact_match_id), site_id, job[6]),
                        )
                        existing = cur.fetchone()
                        if not existing:
                            raise ValueError('content_integrity_failed')
                        snapshot = json.dumps(
                            existing[3], sort_keys=True, separators=(',', ':'), ensure_ascii=False
                        )
                        cur.execute(
                            """INSERT INTO sitecontent_contentrevision
                               (id, content_id, revision, snapshot, actor_ref, created_at,
                                schema_version, snapshot_sha256, action, restored_from_version)
                               VALUES (%s,%s,%s,%s::jsonb,'system:import-worker',NOW(),%s,%s,
                                       'import_update',NULL)""",
                            (
                                str(uuid4()),
                                str(existing[0]),
                                existing[1],
                                snapshot,
                                existing[2],
                                hashlib.sha256(snapshot.encode()).hexdigest(),
                            ),
                        )
                        cur.execute(
                            """UPDATE sitecontent_contentrecord
                               SET slug=%s, title=%s, values=%s::jsonb, version=version+1,
                                   updated_at=NOW()
                               WHERE id=%s AND site_id=%s RETURNING id, version""",
                            (
                                imported['slug'],
                                imported['title'],
                                json.dumps(values),
                                str(existing[0]),
                                site_id,
                            ),
                        )
                        changed = cur.fetchone()
                        if not changed:
                            raise ValueError('content_integrity_failed')
                        result_id, result_version = changed
                        completed_counts['updated'] += 1
                    else:
                        completed_counts['skipped'] += 1
                    cur.execute(
                        """UPDATE sitecontent_importrowoutcome
                           SET result_record_id=%s, result_version=%s, updated_at=NOW()
                           WHERE job_id=%s AND site_id=%s AND ordinal=%s""",
                        (
                            str(result_id) if result_id else None,
                            result_version,
                            str(job_id),
                            site_id,
                            ordinal,
                        ),
                    )
                counters = {
                    'total': len(outcomes),
                    'valid': len(outcomes),
                    'invalid': 0,
                    **completed_counts,
                    'review': 0,
                }
                cur.execute(
                    """UPDATE sitecontent_importjob SET status='completed', counters=%s::jsonb,
                              error_code='', completed_at=NOW(), updated_at=NOW()
                       WHERE id=%s AND site_id=%s AND status='committing' RETURNING id""",
                    (json.dumps(counters), str(job_id), site_id),
                )
                if not cur.fetchone():
                    raise ValueError('content_job_transition_invalid')
                cur.execute(
                    """INSERT INTO sitecontent_workspaceauditevent
                       (id, site_id, actor_ref, object_type, object_ref, action, outcome,
                        correlation_id, metadata, created_at)
                       VALUES (%s,%s,'system:import-worker','import_job',%s,
                               'content.import_complete','accepted','',%s::jsonb,NOW())""",
                    (
                        str(uuid4()),
                        site_id,
                        str(job_id),
                        json.dumps({'count': len(outcomes), 'status': 'completed'}),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return 'completed'
