"""Transactional media processing, export, audit, and governance workers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from api.db import workspace_worker_db_conn as db_conn
from api.services.content_workspace_scanner import ScannerHealth
from api.services.media_inspector_client import MediaInspectorClientError, inspect_media_via_spool
from api.services.media_library_operations import audit_hash, build_export
from api.services.media_library_policy import scanner_is_ready, validate_digest


SAFE_DETAIL_KEYS = frozenset(
    {
        'code',
        'status',
        'version',
        'reason',
        'method',
        'objectVersion',
        'mediaType',
        'byteSize',
        'sha256',
        'count',
    }
)
SAFE_CODE = re.compile(r'^media_[a-z0-9_]{3,63}$')
SAFE_ACTOR = re.compile(r'^[a-z][a-z0-9:._-]{2,199}$')
EXPORT_FIELDS = frozenset(
    {'id', 'filename', 'mediaType', 'byteSize', 'sha256', 'status', 'visibility', 'updatedAt'}
)


class MediaRuntimeError(ValueError):
    pass


@dataclass(frozen=True)
class InspectionOutcome:
    preview: Any
    scanner_ref: str
    definitions_at: datetime
    observed_media_type: str
    result_sha256: str
    decoder_ref: str = 'test:injected'
    measurements: dict[str, int | float] | None = None


def _safe_detail(detail: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict) or set(detail) - SAFE_DETAIL_KEYS:
        raise MediaRuntimeError('media_audit_detail_invalid')
    encoded = json.dumps(detail, sort_keys=True, separators=(',', ':')).encode()
    if len(encoded) > 4096:
        raise MediaRuntimeError('media_audit_detail_invalid')
    for key, value in detail.items():
        if key in {'version', 'objectVersion', 'byteSize', 'count'}:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise MediaRuntimeError('media_audit_detail_invalid')
        elif key == 'sha256':
            validate_digest(value)
        elif not isinstance(value, str) or len(value) > 128 or re.search(r'[\x00-\x1f\x7f]', value):
            raise MediaRuntimeError('media_audit_detail_invalid')
    return detail


def append_media_audit(
    cur,
    *,
    site_id: str,
    event_type: str,
    actor_ref: str,
    subject_ref: str,
    detail: dict[str, Any],
) -> str:
    """Append one serialized, redacted hash-chain member inside the caller transaction."""
    if (
        not re.fullmatch(r'[a-z][a-z0-9-]{2,62}', site_id or '')
        or not re.fullmatch(r'media\.[a-z0-9_.-]{2,58}', event_type or '')
        or not SAFE_ACTOR.fullmatch(actor_ref or '')
        or not re.fullmatch(r'[a-z][a-z0-9:._-]{2,199}', subject_ref or '')
    ):
        raise MediaRuntimeError('media_audit_identity_invalid')
    safe = _safe_detail(detail)
    cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 110))', (site_id,))
    cur.execute(
        """SELECT sequence, event_hash FROM sitecontent_mediaauditevent
           WHERE site_id=%s ORDER BY sequence DESC LIMIT 1 FOR UPDATE""",
        (site_id,),
    )
    previous = cur.fetchone()
    sequence = int(previous[0]) + 1 if previous else 1
    previous_hash = str(previous[1]) if previous else '0' * 64
    event = {
        'eventType': event_type,
        'actorRef': actor_ref,
        'subjectRef': subject_ref,
        'detail': safe,
    }
    digest = audit_hash(previous_hash=previous_hash, sequence=sequence, event=event)
    cur.execute(
        """INSERT INTO sitecontent_mediaauditevent
           (id,site_id,sequence,event_type,actor_ref,subject_ref,detail,
            previous_hash,event_hash,created_at,updated_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,NOW(),NOW())""",
        (
            str(uuid4()),
            site_id,
            sequence,
            event_type,
            actor_ref,
            subject_ref,
            json.dumps(safe, sort_keys=True, separators=(',', ':')),
            previous_hash,
            digest,
        ),
    )
    return digest


def inspect_media_payload(
    *,
    content: bytes,
    expected_sha256: str,
    media_type: str,
    scanner: Callable[[bytes], str],
    health: ScannerHealth,
    observed_at: datetime,
    maximum_signature_age_hours: int,
    probe: Callable[[bytes, str], Any] | None = None,
    preview_builder: Callable[..., Any] | None = None,
) -> InspectionOutcome:
    # Test-only compatibility seam. Production processing always uses the
    # isolated inspector client and does not import decoders into this worker.
    if probe is None:
        from api.services.media_library_parser import probe_media_no_network

        probe = probe_media_no_network
    if preview_builder is None:
        from api.services.media_library_processor import generate_media_preview

        preview_builder = generate_media_preview
    validate_digest(expected_sha256)
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise MediaRuntimeError('media_integrity_failed')
    if not scanner_is_ready(
        engine=health.engine,
        definitions_updated_at=health.definitions_updated_at,
        observed_at=observed_at,
        maximum_age_hours=maximum_signature_age_hours,
    ):
        raise MediaRuntimeError('media_scanner_stale')
    if not re.fullmatch(r'[0-9][A-Za-z0-9._-]{0,31}', health.engine_version or ''):
        raise MediaRuntimeError('media_scanner_identity_invalid')
    if not re.fullmatch(r'[0-9]{1,12}', health.definitions_version or ''):
        raise MediaRuntimeError('media_scanner_identity_invalid')
    verdict = scanner(content)
    if verdict == 'infected':
        raise MediaRuntimeError('media_inspection_rejected')
    if verdict != 'clean':
        raise MediaRuntimeError('media_scanner_response_invalid')
    if media_type.startswith(('audio/', 'video/')):
        probe(content, media_type)
    preview = preview_builder(content=content, media_type=media_type)
    preview_digest = hashlib.sha256(preview.content).hexdigest()
    if preview_digest != preview.sha256:
        raise MediaRuntimeError('media_derivative_integrity_failed')
    scanner_ref = f'clamav:{health.engine_version}-{health.definitions_version}'
    result = hashlib.sha256(
        f'{expected_sha256}\0{preview_digest}\0{scanner_ref}\0{health.definitions_updated_at.isoformat()}'.encode()
    ).hexdigest()
    return InspectionOutcome(
        preview, scanner_ref, health.definitions_updated_at, media_type, result
    )


def process_governed_media_asset(
    *,
    site_id: str,
    asset_id: UUID,
    artifact_store,
    scanner: Callable[[bytes], str] | None = None,
    health_reader: Callable[[], ScannerHealth] | None = None,
    observed_at: datetime | None = None,
    maximum_signature_age_hours: int = 24,
    inspector: Callable[..., InspectionOutcome] | None = None,
) -> str:
    observed = observed_at or datetime.now(UTC)
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT storage_key,sha256,status,media_type,byte_size,
                              current_object_version,lock_version
                       FROM sitecontent_mediaasset
                       WHERE site_id=%s AND id=%s FOR UPDATE""",
                    (site_id, str(asset_id)),
                )
                row = cur.fetchone()
                if not row:
                    return 'not_found'
                if row[2] in {'ready', 'rejected', 'purged'}:
                    return f'already_{row[2]}'
                if row[2] != 'quarantined':
                    return 'not_ready'
                content = artifact_store.get(row[0], expected_sha256=row[1])
                try:
                    if inspector is None:
                        isolated = inspect_media_via_spool(
                            content=content,
                            expected_sha256=row[1],
                            media_type=row[3],
                            asset_id=asset_id,
                            object_version=int(row[5]),
                            observed_at=observed,
                        )
                        outcome = InspectionOutcome(
                            isolated.preview,
                            isolated.scanner_ref,
                            isolated.definitions_at,
                            isolated.observed_media_type,
                            isolated.result_sha256,
                            isolated.decoder_ref,
                            isolated.measurements,
                        )
                    else:
                        if scanner is None:
                            from api.services.content_workspace_scanner import scan_content

                            scanner = scan_content
                        if health_reader is None:
                            from api.services.content_workspace_scanner import clamav_health

                            health_reader = clamav_health
                        outcome = inspector(
                            content=content,
                            expected_sha256=row[1],
                            media_type=row[3],
                            scanner=scanner,
                            health=health_reader(),
                            observed_at=observed,
                            maximum_signature_age_hours=maximum_signature_age_hours,
                        )
                except (MediaRuntimeError, MediaInspectorClientError) as exc:
                    code = (
                        str(exc)
                        if SAFE_CODE.fullmatch(str(exc))
                        else 'media_dependency_unavailable'
                    )
                    rejected = code == 'media_inspection_rejected'
                    cur.execute(
                        """INSERT INTO sitecontent_mediajob
                           (id,site_id,asset_id,kind,status,idempotency_key,request_digest,attempt,
                            maximum_attempts,error_code,output_digest,available_at,completed_at,
                            created_at,updated_at)
                           VALUES (%s,%s,%s,'inspect',%s,%s,%s,1,3,%s,'',NOW(),
                                   CASE WHEN %s THEN NOW() ELSE NULL END,NOW(),NOW())
                           ON CONFLICT (site_id,kind,idempotency_key) DO UPDATE SET
                             attempt=LEAST(sitecontent_mediajob.attempt+1,
                                           sitecontent_mediajob.maximum_attempts),
                             status=CASE
                               WHEN %s THEN 'failed'
                               WHEN sitecontent_mediajob.attempt+1 >=
                                    sitecontent_mediajob.maximum_attempts THEN 'failed'
                               ELSE 'retryable' END,
                             error_code=EXCLUDED.error_code,
                             available_at=NOW(),
                             completed_at=CASE
                               WHEN %s OR sitecontent_mediajob.attempt+1 >=
                                    sitecontent_mediajob.maximum_attempts THEN NOW()
                               ELSE NULL END,
                             updated_at=NOW()
                           RETURNING status,attempt,maximum_attempts""",
                        (
                            str(uuid4()),
                            site_id,
                            str(asset_id),
                            'failed' if rejected else 'retryable',
                            f'inspect:{asset_id}:{row[5]}',
                            row[1],
                            code,
                            rejected,
                            rejected,
                            rejected,
                        ),
                    )
                    job = cur.fetchone()
                    if not job:
                        raise MediaRuntimeError('media_job_state_invalid') from exc
                    if job[0] == 'retryable':
                        retry_delay = min(300, 15 * (2 ** (int(job[1]) - 1)))
                        cur.execute(
                            """UPDATE sitecontent_mediajob
                               SET available_at=NOW()+(%s*INTERVAL '1 second'),updated_at=NOW()
                               WHERE site_id=%s AND kind='inspect' AND idempotency_key=%s
                                 AND status='retryable' AND attempt=%s""",
                            (
                                retry_delay,
                                site_id,
                                f'inspect:{asset_id}:{row[5]}',
                                int(job[1]),
                            ),
                        )
                        if cur.rowcount != 1:
                            raise MediaRuntimeError('media_job_state_invalid') from exc
                    next_state = 'rejected' if rejected else (
                        'failed' if job[0] == 'failed' else 'quarantined'
                    )
                    cur.execute(
                        """UPDATE sitecontent_mediaasset
                           SET status=%s,
                               lock_version=lock_version+1,updated_at=NOW()
                           WHERE site_id=%s AND id=%s AND lock_version=%s""",
                        (next_state, site_id, str(asset_id), row[6]),
                    )
                    append_media_audit(
                        cur,
                        site_id=site_id,
                        event_type='media.inspection.failed',
                        actor_ref='system:media-worker',
                        subject_ref=f'asset:{asset_id}',
                        detail={
                            'code': code,
                            'status': next_state,
                            'count': int(job[1]),
                            'sha256': row[1],
                        },
                    )
                    conn.commit()
                    return next_state
                stored = artifact_store.put(
                    namespace='variants',
                    site_id=site_id,
                    object_id=f'{asset_id}-v{row[5]}-safe',
                    content=outcome.preview.content,
                )
                if stored.sha256 != outcome.preview.sha256:
                    raise MediaRuntimeError('media_derivative_integrity_failed')
                cur.execute(
                    """INSERT INTO sitecontent_mediaobjectversion
                       (id,site_id,asset_id,version,storage_key,sha256,byte_size,detected_type,
                        inspection_state,scanner_ref,scanner_definitions_at,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'accepted',%s,%s,NOW(),NOW())
                       ON CONFLICT (asset_id,version) DO NOTHING""",
                    (
                        str(uuid4()),
                        site_id,
                        str(asset_id),
                        row[5],
                        row[0],
                        row[1],
                        row[4],
                        outcome.observed_media_type,
                        outcome.scanner_ref,
                        outcome.definitions_at,
                    ),
                )
                cur.execute(
                    """SELECT id FROM sitecontent_mediaobjectversion
                       WHERE site_id=%s AND asset_id=%s AND version=%s AND sha256=%s""",
                    (site_id, str(asset_id), row[5], row[1]),
                )
                object_row = cur.fetchone()
                if not object_row:
                    raise MediaRuntimeError('media_object_version_conflict')
                cur.execute(
                    """INSERT INTO sitecontent_mediainspectionresult
                       (id,site_id,object_version_id,attempt,decision,safe_code,scanner_ref,
                        decoder_ref,definitions_at,observed_media_type,measurements,result_sha256,
                        created_at,updated_at)
                       VALUES (%s,%s,%s,1,'accepted','media_inspection_accepted',%s,
                               %s,%s,%s,%s::jsonb,%s,NOW(),NOW())
                       ON CONFLICT (object_version_id,attempt) DO NOTHING""",
                    (
                        str(uuid4()),
                        site_id,
                        str(object_row[0]),
                        outcome.scanner_ref,
                        outcome.decoder_ref,
                        outcome.definitions_at,
                        outcome.observed_media_type,
                        json.dumps(
                            outcome.measurements or {}, sort_keys=True, separators=(',', ':')
                        ),
                        outcome.result_sha256,
                    ),
                )
                cur.execute(
                    """INSERT INTO sitecontent_mediavariant
                       (id,asset_id,name,storage_key,media_type,byte_size,sha256,width,height,
                        recipe_id,recipe_version,source_sha256,processor_ref,inline_safe,created_at)
                       VALUES (%s,%s,'safe',%s,%s,%s,%s,%s,%s,'safe-preview',1,%s,
                               %s,%s,NOW())
                       ON CONFLICT (asset_id,name) DO UPDATE SET
                         storage_key=EXCLUDED.storage_key,media_type=EXCLUDED.media_type,
                         byte_size=EXCLUDED.byte_size,sha256=EXCLUDED.sha256,
                         width=EXCLUDED.width,height=EXCLUDED.height,
                         source_sha256=EXCLUDED.source_sha256,processor_ref=EXCLUDED.processor_ref,
                         inline_safe=EXCLUDED.inline_safe""",
                    (
                        str(uuid4()),
                        str(asset_id),
                        stored.object_key,
                        outcome.preview.media_type,
                        stored.byte_size,
                        stored.sha256,
                        outcome.preview.width,
                        outcome.preview.height,
                        row[1],
                        outcome.decoder_ref,
                        outcome.preview.media_type.startswith('image/'),
                    ),
                )
                cur.execute(
                    """INSERT INTO sitecontent_mediajob
                       (id,site_id,asset_id,kind,status,idempotency_key,request_digest,attempt,
                        maximum_attempts,error_code,output_digest,available_at,completed_at,
                        created_at,updated_at)
                       VALUES (%s,%s,%s,'inspect','completed',%s,%s,1,3,'',%s,NOW(),NOW(),NOW(),NOW())
                       ON CONFLICT (site_id,kind,idempotency_key) DO UPDATE SET
                         status='completed',
                         attempt=LEAST(sitecontent_mediajob.attempt+1,
                                       sitecontent_mediajob.maximum_attempts),
                         error_code='',output_digest=EXCLUDED.output_digest,
                         completed_at=NOW(),updated_at=NOW()""",
                    (
                        str(uuid4()),
                        site_id,
                        str(asset_id),
                        f'inspect:{asset_id}:{row[5]}',
                        row[1],
                        outcome.result_sha256,
                    ),
                )
                cur.execute(
                    """UPDATE sitecontent_mediaasset
                       SET status='ready',lock_version=lock_version+1,updated_at=NOW()
                       WHERE site_id=%s AND id=%s AND lock_version=%s RETURNING lock_version""",
                    (site_id, str(asset_id), row[6]),
                )
                updated = cur.fetchone()
                if not updated:
                    raise MediaRuntimeError('media_version_conflict')
                append_media_audit(
                    cur,
                    site_id=site_id,
                    event_type='media.inspection.completed',
                    actor_ref='system:media-worker',
                    subject_ref=f'asset:{asset_id}',
                    detail={
                        'status': 'ready',
                        'version': int(updated[0]),
                        'sha256': row[1],
                        'mediaType': row[3],
                        'byteSize': int(row[4]),
                    },
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return 'ready'


def normalize_export_selection(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {'fields', 'assetIds', 'filters'}:
        raise MediaRuntimeError('media_export_selection_required')
    fields, asset_ids, filters = value['fields'], value['assetIds'], value['filters']
    if (
        not isinstance(fields, list)
        or not fields
        or len(fields) != len(set(fields))
        or set(fields) - EXPORT_FIELDS
        or not isinstance(asset_ids, list)
        or not 1 <= len(asset_ids) <= 10_000
        or len(asset_ids) != len(set(asset_ids))
        or filters != {}
    ):
        raise MediaRuntimeError('media_export_selection_invalid')
    try:
        normalized_ids = sorted(str(UUID(item)) for item in asset_ids)
    except (ValueError, TypeError, AttributeError) as exc:
        raise MediaRuntimeError('media_export_selection_invalid') from exc
    return {'fields': fields, 'assetIds': normalized_ids, 'filters': filters}


def due_media_exports(*, limit: int = 10) -> list[tuple[str, str]]:
    if not 1 <= limit <= 50:
        raise MediaRuntimeError('media_limit_invalid')
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT site_id,id FROM sitecontent_mediaexportpackage
               WHERE status='queued' AND expires_at>NOW()
               ORDER BY created_at,id LIMIT %s""",
            (limit,),
        )
        return [(row[0], str(row[1])) for row in cur.fetchall()]


def process_media_export(
    *,
    site_id: str,
    export_id: UUID,
    artifact_store,
) -> str:
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT status,output_format,projection,requested_by,request_digest,expires_at
                       FROM sitecontent_mediaexportpackage
                       WHERE site_id=%s AND id=%s FOR UPDATE""",
                    (site_id, str(export_id)),
                )
                package = cur.fetchone()
                if not package:
                    return 'not_found'
                if package[0] == 'ready':
                    return 'already_ready'
                if package[0] != 'queued' or package[5] <= datetime.now(UTC):
                    return 'not_ready'
                selection = normalize_export_selection(package[2])
                cur.execute(
                    """SELECT id,original_name,media_type,byte_size,sha256,status,visibility,updated_at
                       FROM sitecontent_mediaasset
                       WHERE site_id=%s AND id=ANY(%s::uuid[]) AND status<>'purged'
                         AND (owner_ref=%s OR visibility IN ('authenticated','public'))
                       ORDER BY id LIMIT 10000""",
                    (site_id, selection['assetIds'], package[3]),
                )
                rows = cur.fetchall()
                if {str(row[0]) for row in rows} != set(selection['assetIds']):
                    raise MediaRuntimeError('media_export_asset_missing')
                payload = [
                    {
                        'id': str(row[0]),
                        'filename': row[1],
                        'mediaType': row[2],
                        'byteSize': int(row[3]),
                        'sha256': row[4],
                        'status': row[5],
                        'visibility': row[6],
                        'updatedAt': row[7].isoformat(),
                    }
                    for row in rows
                ]
                output = build_export(
                    payload, output_format=package[1], fields=tuple(selection['fields'])
                )
                stored = artifact_store.put(
                    namespace='media-exports',
                    site_id=site_id,
                    object_id=str(export_id),
                    content=output,
                )
                cur.execute(
                    """UPDATE sitecontent_mediaexportpackage
                       SET status='ready',artifact_key=%s,artifact_sha256=%s,updated_at=NOW()
                       WHERE site_id=%s AND id=%s AND status='queued'""",
                    (stored.object_key, stored.sha256, site_id, str(export_id)),
                )
                append_media_audit(
                    cur,
                    site_id=site_id,
                    event_type='media.export.completed',
                    actor_ref='system:media-worker',
                    subject_ref=f'export:{export_id}',
                    detail={'status': 'ready', 'count': len(rows), 'sha256': stored.sha256},
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return 'ready'


def apply_due_media_governance(*, limit: int = 100) -> dict[str, int]:
    """Expire due holds and enforce already-reviewed abuse decisions; never approve them."""
    if not 1 <= limit <= 500:
        raise MediaRuntimeError('media_limit_invalid')
    with db_conn() as discovery, discovery.cursor() as cur:
        cur.execute(
            """SELECT site_id,id FROM sitecontent_mediaretentionhold
               WHERE active=TRUE AND expires_at IS NOT NULL AND expires_at<=NOW()
               ORDER BY expires_at,id LIMIT %s""",
            (limit,),
        )
        hold_candidates = [(str(site), str(identifier)) for site, identifier in cur.fetchall()]
        cur.execute(
            """SELECT c.site_id,c.id FROM sitecontent_mediaabusecase c
               JOIN sitecontent_mediaasset a ON a.id=c.asset_id AND a.site_id=c.site_id
               WHERE (c.status='quarantined'
                      AND a.status NOT IN ('archived','soft_deleted','purged'))
                  OR (c.status='removed' AND a.status NOT IN ('soft_deleted','purged'))
               ORDER BY c.updated_at,c.id LIMIT %s""",
            (limit,),
        )
        case_candidates = [(str(site), str(identifier)) for site, identifier in cur.fetchall()]

    sites = sorted({site for site, _identifier in hold_candidates + case_candidates})
    holds = cases = 0
    for site in sites:
        hold_ids = [identifier for candidate_site, identifier in hold_candidates if candidate_site == site]
        case_ids = [identifier for candidate_site, identifier in case_candidates if candidate_site == site]
        with db_conn(tenant_id=site) as conn:
            try:
                with conn.cursor() as cur:
                    expired = []
                    if hold_ids:
                        cur.execute(
                            """UPDATE sitecontent_mediaretentionhold
                               SET active=FALSE,updated_at=NOW()
                               WHERE site_id=%s AND id=ANY(%s::uuid[]) AND active=TRUE
                                 AND expires_at IS NOT NULL AND expires_at<=NOW()
                               RETURNING asset_id,reason_code""",
                            (site, hold_ids),
                        )
                        expired = cur.fetchall()
                    holds += len(expired)
                    for asset, reason in expired:
                        append_media_audit(
                            cur,
                            site_id=site,
                            event_type='media.hold.expired',
                            actor_ref='system:media-worker',
                            subject_ref=f'asset:{asset}',
                            detail={'status': 'expired', 'reason': reason},
                        )
                    decisions = []
                    if case_ids:
                        cur.execute(
                            """SELECT c.id,c.asset_id,c.status,a.status,a.lock_version
                               FROM sitecontent_mediaabusecase c
                               JOIN sitecontent_mediaasset a
                                 ON a.id=c.asset_id AND a.site_id=c.site_id
                               WHERE c.site_id=%s AND c.id=ANY(%s::uuid[])
                                 AND ((c.status='quarantined'
                                       AND a.status NOT IN ('archived','soft_deleted','purged'))
                                   OR (c.status='removed'
                                       AND a.status NOT IN ('soft_deleted','purged')))
                               ORDER BY c.updated_at,c.id FOR UPDATE OF c,a""",
                            (site, case_ids),
                        )
                        decisions = cur.fetchall()
                    for case_id, asset_id, decision, _state, version in decisions:
                        target = 'archived' if decision == 'quarantined' else 'soft_deleted'
                        cur.execute(
                            """UPDATE sitecontent_mediaasset
                               SET status=%s,authorization_epoch=authorization_epoch+1,
                                   lock_version=lock_version+1,updated_at=NOW()
                               WHERE site_id=%s AND id=%s AND lock_version=%s""",
                            (target, site, str(asset_id), version),
                        )
                        if cur.rowcount != 1:
                            raise MediaRuntimeError('media_version_conflict')
                        cur.execute(
                            """UPDATE sitecontent_mediadeliverygrant
                               SET revoked_at=NOW(),updated_at=NOW()
                               WHERE site_id=%s AND asset_id=%s AND revoked_at IS NULL""",
                            (site, str(asset_id)),
                        )
                        append_media_audit(
                            cur,
                            site_id=site,
                            event_type='media.abuse.enforced',
                            actor_ref='system:media-worker',
                            subject_ref=f'asset:{asset_id}',
                            detail={
                                'status': target,
                                'reason': f'case:{case_id}',
                                'version': int(version) + 1,
                            },
                        )
                        cases += 1
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    return {'holdsExpired': holds, 'abuseCasesEnforced': cases}
