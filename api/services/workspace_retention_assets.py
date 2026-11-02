"""Legacy local retention with committed, database-authorized immutable purge plans.

Only short claim/finalization transactions take the policy lock. Encrypted local
object IO (up to 128 objects, each at most 100 MiB) runs after the claim commits.
A crash leaves a frozen purge intent, never a restorable partially deleted asset.
Remote/governed storage is deliberately not supported by this compatibility seam.
"""

from __future__ import annotations

import hashlib
import json
import re
from uuid import UUID

from api.db import workspace_worker_db_conn as db_conn
from api.services.content_workspace_storage import (
    ArtifactIntegrityError,
    PrivateArtifactStore,
    SHA256,
)

MAX_OBJECTS = 128
MAX_OBJECT_BYTES = 100 * 1024 * 1024


def _manifest(objects, *, site_id: str, asset_id: str):
    """Validate the entire committed manifest before the first irreversible IO."""
    if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_OBJECTS:
        raise ValueError('content_retention_manifest_invalid')
    seen = set()
    originals = 0
    for item in objects:
        if not isinstance(item, dict) or set(item) != {
            'namespace',
            'object_id',
            'object_key',
            'sha256',
            'byte_size',
        }:
            raise ValueError('content_retention_manifest_invalid')
        namespace, object_id = item['namespace'], item['object_id']
        if namespace == 'media' and object_id == asset_id:
            originals += 1
        elif (
            namespace != 'variants'
            or not isinstance(object_id, str)
            or not re.fullmatch(
                re.escape(asset_id) + r'-(?:v[1-9][0-9]*-)?[a-zA-Z0-9_-]{1,64}', object_id
            )
        ):
            raise ValueError('content_artifact_owner_mismatch')
        expected_key = PrivateArtifactStore.object_key(
            namespace=namespace, site_id=site_id, object_id=object_id
        )
        if item['object_key'] != expected_key or expected_key in seen:
            raise ValueError('content_artifact_owner_mismatch')
        if not isinstance(item['sha256'], str) or not SHA256.fullmatch(item['sha256']):
            raise ValueError('content_integrity_failed')
        if type(item['byte_size']) is not int or not 1 <= item['byte_size'] <= MAX_OBJECT_BYTES:
            raise ValueError('content_limit_exceeded')
        seen.add(expected_key)
    if originals != 1:
        raise ValueError('content_retention_manifest_invalid')
    return objects


def _claim(*, site_id, asset_id):
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT plan_id,object_manifest FROM base2_claim_workspace_asset_purge(%s,%s)',
                    (site_id, asset_id),
                )
                row = cur.fetchone()
            conn.commit()
            return row
        except Exception:
            conn.rollback()
            raise


def _complete(*, site_id, plan_id, digest):
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT base2_complete_workspace_asset_purge(%s,%s,%s)',
                    (site_id, plan_id, digest),
                )
                row = cur.fetchone()
                if not row or type(row[0]) is not bool:
                    raise ValueError('content_retention_completion_invalid')
            conn.commit()
            return row[0]
        except Exception:
            conn.rollback()
            raise


def purge_workspace_assets(*, artifact_store, site_id: str, limit: int = 100) -> int:
    """Return newly completed physical purges, retaining canonical audit tombstones."""
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('content_limit_exceeded')
    # Do not claim/mutate unsupported remote or custom storage transports.
    if type(artifact_store) is not PrivateArtifactStore:
        raise ValueError('content_retention_local_storage_required')
    PrivateArtifactStore.object_key(namespace='media', site_id=site_id, object_id='validation')
    with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id FROM sitecontent_mediaasset
               WHERE site_id=%s AND (status='purge_planned' OR
                 (status='deleted' AND retention_until<=NOW()))
               ORDER BY retention_until,id LIMIT %s""",
            (site_id, limit),
        )
        candidates = cur.fetchall()
    completed = 0
    for (candidate,) in candidates:
        asset_id = str(UUID(str(candidate)))
        claim = _claim(site_id=site_id, asset_id=asset_id)
        if not claim:
            continue
        plan_id, raw_manifest = claim
        objects = _manifest(raw_manifest, site_id=site_id, asset_id=asset_id)
        for item in objects:
            try:
                artifact_store.delete(
                    namespace=item['namespace'],
                    site_id=site_id,
                    object_id=item['object_id'],
                    object_key=item['object_key'],
                    expected_sha256=item['sha256'],
                    missing_ok=False,
                )
            except ArtifactIntegrityError as exc:
                # The store uses the same public error for absence and other OS
                # failures. Only positively identified absence is a safe retry.
                if not (
                    str(exc) == 'content_artifact_unavailable'
                    and isinstance(exc.__cause__, FileNotFoundError)
                ):
                    raise
        digest = hashlib.sha256(
            json.dumps(objects, sort_keys=True, separators=(',', ':')).encode()
        ).hexdigest()
        completed += int(_complete(site_id=site_id, plan_id=str(plan_id), digest=digest))
    return completed
