"""Tenant-scoped persistence for the media library read and metadata surfaces."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from api.db import workspace_db_conn as db_conn


def _asset(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        'id': str(row[0]),
        'filename': row[1],
        'mediaType': row[2],
        'byteSize': int(row[3]),
        'sha256': row[4],
        'status': row[5],
        'visibility': row[6],
        'version': int(row[7]),
        'updatedAt': row[8].isoformat() if hasattr(row[8], 'isoformat') else row[8],
    }


class PostgresMediaLibraryRepository:
    """Every query carries site scope; callers never provide storage keys."""

    def list_assets(
        self,
        *,
        site_id: str,
        limit: int,
        offset: int,
        state: str | None = None,
        media_type: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        clauses = ['site_id=%s', "status<>'purged'"]
        params: list[Any] = [site_id]
        if state:
            clauses.append('status=%s')
            params.append(state)
        if media_type:
            clauses.append('media_type=%s')
            params.append(media_type)
        if search:
            clauses.append('original_name ILIKE %s')
            params.append(f'%{search}%')
        where = ' AND '.join(clauses)
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, original_name, media_type, byte_size, sha256, status,
                            visibility, lock_version, updated_at
                     FROM sitecontent_mediaasset
                     WHERE {where}
                     ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s""",
                (*params, limit + 1, offset),
            )
            rows = cur.fetchall()
        more = len(rows) > limit
        return {
            'items': [_asset(row) for row in rows[:limit]],
            'nextOffset': offset + limit if more else None,
            'indexStatus': 'current',
        }

    def get_asset(self, *, site_id: str, asset_id: UUID) -> dict[str, Any]:
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT id, original_name, media_type, byte_size, sha256, status,
                          visibility, lock_version, updated_at
                   FROM sitecontent_mediaasset
                   WHERE site_id=%s AND id=%s AND status<>'purged'""",
                (site_id, str(asset_id)),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError('media_not_found')
            cur.execute(
                """SELECT name, media_type, byte_size, sha256, width, height,
                          recipe_id, recipe_version, inline_safe
                   FROM sitecontent_mediavariant
                   WHERE asset_id=%s ORDER BY name""",
                (str(asset_id),),
            )
            variants = cur.fetchall()
        result = _asset(row)
        result['variants'] = [
            {
                'name': item[0],
                'mediaType': item[1],
                'byteSize': int(item[2]),
                'sha256': item[3],
                'width': item[4],
                'height': item[5],
                'recipeId': item[6],
                'recipeVersion': int(item[7]),
                'inlineSafe': bool(item[8]),
            }
            for item in variants
        ]
        return result

    def update_metadata(
        self,
        *,
        site_id: str,
        asset_id: UUID,
        actor_ref: str,
        expected_version: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT lock_version, media_type FROM sitecontent_mediaasset
                           WHERE site_id=%s AND id=%s AND status NOT IN ('purged','soft_deleted')
                           FOR UPDATE""",
                        (site_id, str(asset_id)),
                    )
                    current = cur.fetchone()
                    if not current:
                        raise ValueError('media_not_found')
                    if int(current[0]) != expected_version:
                        raise ValueError('media_version_conflict')
                    decorative = bool(payload['decorative'])
                    if (
                        current[1].startswith('image/')
                        and not decorative
                        and not payload['altText'].strip()
                    ):
                        raise ValueError('media_alt_or_decorative_required')
                    cur.execute(
                        """SELECT COALESCE(MAX(revision),0)+1
                           FROM sitecontent_mediametadatarevision
                           WHERE site_id=%s AND asset_id=%s AND locale=%s""",
                        (site_id, str(asset_id), payload['locale']),
                    )
                    revision = int(cur.fetchone()[0])
                    cur.execute(
                        """INSERT INTO sitecontent_mediametadatarevision
                           (id, site_id, asset_id, revision, locale, alt_text, decorative,
                            caption, credit, license_code, focal_x, focal_y, actor_ref,
                            created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())""",
                        (
                            str(uuid4()),
                            site_id,
                            str(asset_id),
                            revision,
                            payload['locale'],
                            payload['altText'],
                            decorative,
                            payload['caption'],
                            payload['credit'],
                            payload['licenseCode'],
                            payload['focalX'],
                            payload['focalY'],
                            actor_ref,
                        ),
                    )
                    cur.execute(
                        """UPDATE sitecontent_mediaasset
                           SET visibility=%s, lock_version=lock_version+1, updated_at=NOW()
                           WHERE site_id=%s AND id=%s AND lock_version=%s
                           RETURNING lock_version""",
                        (payload['visibility'], site_id, str(asset_id), expected_version),
                    )
                    next_version = int(cur.fetchone()[0])
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {'id': str(asset_id), 'revision': revision, 'version': next_version}

    def list_references(self, *, site_id: str, asset_id: UUID) -> dict[str, Any]:
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT id, owner_type, owner_id, field_key, owner_state,
                          owner_visibility, required, lock_version
                   FROM sitecontent_mediareference
                   WHERE site_id=%s AND asset_id=%s
                   ORDER BY owner_type, owner_id, field_key""",
                (site_id, str(asset_id)),
            )
            rows = cur.fetchall()
        return {
            'items': [
                {
                    'id': str(row[0]),
                    'ownerType': row[1],
                    'ownerId': str(row[2]),
                    'fieldKey': row[3],
                    'ownerState': row[4],
                    'ownerVisibility': row[5],
                    'required': bool(row[6]),
                    'version': int(row[7]),
                }
                for row in rows
            ]
        }

    def destructive_preview(self, *, site_id: str, asset_id: UUID) -> dict[str, Any]:
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT lock_version, status FROM sitecontent_mediaasset
                   WHERE site_id=%s AND id=%s AND status<>'purged'""",
                (site_id, str(asset_id)),
            )
            asset = cur.fetchone()
            if not asset:
                raise ValueError('media_not_found')
            cur.execute(
                """SELECT owner_type, owner_id, field_key, owner_state, required
                   FROM sitecontent_mediareference
                   WHERE site_id=%s AND asset_id=%s
                   ORDER BY owner_type, owner_id, field_key""",
                (site_id, str(asset_id)),
            )
            references = cur.fetchall()
            cur.execute(
                """SELECT reason_code FROM sitecontent_mediaretentionhold
                   WHERE site_id=%s AND asset_id=%s AND active=TRUE
                   ORDER BY reason_code""",
                (site_id, str(asset_id)),
            )
            holds = cur.fetchall()
            cur.execute(
                """SELECT version, sha256, byte_size FROM sitecontent_mediaobjectversion
                   WHERE site_id=%s AND asset_id=%s ORDER BY version""",
                (site_id, str(asset_id)),
            )
            objects = cur.fetchall()
        blocking = [
            {
                'ownerType': row[0],
                'ownerId': str(row[1]),
                'fieldKey': row[2],
                'ownerState': row[3],
                'required': bool(row[4]),
            }
            for row in references
            if row[4] or row[3] == 'published'
        ]
        return {
            'assetId': str(asset_id),
            'version': int(asset[0]),
            'status': asset[1],
            'allowed': not blocking and not holds,
            'blockingReferences': blocking,
            'activeHolds': [row[0] for row in holds],
            'objects': [
                {'version': int(row[0]), 'sha256': row[1], 'byteSize': int(row[2])}
                for row in objects
            ],
            'proposedEffects': [
                'revoke_delivery',
                'delete_derivatives',
                'delete_original',
                'retain_audit',
            ],
        }

    def transition_asset(
        self,
        *,
        site_id: str,
        asset_id: UUID,
        actor_ref: str,
        target: str,
        expected_version: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        transitions = {
            'ready': {'archived', 'soft_deleted'},
            'archived': {'ready', 'soft_deleted'},
            'soft_deleted': {'ready', 'purge_planned'},
        }
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT lock_version, status FROM sitecontent_mediaasset
                           WHERE site_id=%s AND id=%s AND status<>'purged' FOR UPDATE""",
                        (site_id, str(asset_id)),
                    )
                    current = cur.fetchone()
                    if not current:
                        raise ValueError('media_not_found')
                    if int(current[0]) != expected_version:
                        raise ValueError('media_version_conflict')
                    if target not in transitions.get(current[1], set()):
                        raise ValueError('media_transition_invalid')
                    if target in {'soft_deleted', 'purge_planned'}:
                        cur.execute(
                            """SELECT EXISTS(
                                   SELECT 1 FROM sitecontent_mediareference
                                   WHERE site_id=%s AND asset_id=%s
                                     AND (required=TRUE OR owner_state='published')
                               ), EXISTS(
                                   SELECT 1 FROM sitecontent_mediaretentionhold
                                   WHERE site_id=%s AND asset_id=%s AND active=TRUE
                               )""",
                            (site_id, str(asset_id), site_id, str(asset_id)),
                        )
                        blocked = cur.fetchone()
                        if blocked and any(blocked):
                            raise ValueError('media_transition_blocked')
                    replay_digest = hashlib.sha256(
                        f'{site_id}\0{asset_id}\0{target}\0{expected_version}'.encode()
                    ).hexdigest()
                    cur.execute(
                        """INSERT INTO sitecontent_mediaoutboxevent
                           (id, site_id, aggregate_ref, event_kind, idempotency_key,
                            payload_digest, status, attempt, maximum_attempts, available_at,
                            error_code, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,'pending',0,5,NOW(),'',NOW(),NOW())
                           ON CONFLICT (site_id, event_kind, idempotency_key) DO NOTHING
                           RETURNING id""",
                        (
                            str(uuid4()),
                            site_id,
                            f'asset:{asset_id}',
                            f'asset.{target}',
                            idempotency_key,
                            replay_digest,
                        ),
                    )
                    outbox = cur.fetchone()
                    if not outbox:
                        cur.execute(
                            """SELECT lock_version, status FROM sitecontent_mediaasset
                               WHERE site_id=%s AND id=%s""",
                            (site_id, str(asset_id)),
                        )
                        replayed = cur.fetchone()
                        if replayed and replayed[1] == target:
                            conn.rollback()
                            return {
                                'id': str(asset_id),
                                'status': target,
                                'version': int(replayed[0]),
                                'replayed': True,
                            }
                        raise ValueError('media_idempotency_conflict')
                    cur.execute(
                        """UPDATE sitecontent_mediaasset
                           SET status=%s, lock_version=lock_version+1,
                               archived_at=CASE WHEN %s='archived' THEN NOW() ELSE archived_at END,
                               deleted_at=CASE WHEN %s='soft_deleted' THEN NOW()
                                               WHEN %s='ready' THEN NULL ELSE deleted_at END,
                               updated_at=NOW()
                           WHERE site_id=%s AND id=%s AND lock_version=%s
                           RETURNING lock_version""",
                        (
                            target,
                            target,
                            target,
                            target,
                            site_id,
                            str(asset_id),
                            expected_version,
                        ),
                    )
                    updated = cur.fetchone()
                    if not updated:
                        raise ValueError('media_version_conflict')
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            'id': str(asset_id),
            'status': target,
            'version': int(updated[0]),
            'replayed': False,
        }

    def create_export(
        self,
        *,
        site_id: str,
        actor_ref: str,
        output_format: str,
        projection: list[str],
        request_digest: str,
        expires_at,
    ) -> dict[str, Any]:
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    identifier = uuid4()
                    cur.execute(
                        """INSERT INTO sitecontent_mediaexportpackage
                           (id, site_id, requested_by, output_format, projection, status,
                            artifact_key, artifact_sha256, request_digest, expires_at,
                            error_code, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,'queued','','',%s,%s,'',NOW(),NOW())
                           ON CONFLICT (site_id, requested_by, request_digest) DO NOTHING
                           RETURNING id, status, expires_at""",
                        (
                            str(identifier),
                            site_id,
                            actor_ref,
                            output_format,
                            json.dumps(projection),
                            request_digest,
                            expires_at,
                        ),
                    )
                    row = cur.fetchone()
                    replayed = row is None
                    if replayed:
                        cur.execute(
                            """SELECT id, status, expires_at FROM sitecontent_mediaexportpackage
                               WHERE site_id=%s AND requested_by=%s AND request_digest=%s""",
                            (site_id, actor_ref, request_digest),
                        )
                        row = cur.fetchone()
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            'id': str(row[0]),
            'status': row[1],
            'expiresAt': row[2].isoformat() if hasattr(row[2], 'isoformat') else row[2],
            'replayed': replayed,
        }
