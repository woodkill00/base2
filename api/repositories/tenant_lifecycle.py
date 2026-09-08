"""Durable, replay-safe tenant lifecycle persistence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from api.db import workspace_db_conn

NONCE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')


class TenantLifecycleRepositoryError(ValueError):
    pass


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()


def _state_row(cursor, tenant_id: str, *, lock: bool = False):
    cursor.execute(
        """SELECT state,owner_ref,configuration,revision,last_operation_id,last_receipt_digest
             FROM sitecontent_tenantlifecyclestate
            WHERE site_id=%s"""
        + (' FOR UPDATE' if lock else ''),
        (tenant_id,),
    )
    return cursor.fetchone()


def _serialized_state(tenant_id: str, row, *, idempotent: bool = False) -> dict[str, Any]:
    if not row:
        raise TenantLifecycleRepositoryError('tenant:lifecycle_missing')
    return {
        'tenantId': tenant_id,
        'state': str(row[0]),
        'owner': str(row[1]),
        'configuration': dict(row[2] or {}),
        'revision': int(row[3]),
        'operationId': str(row[4]),
        'receiptDigest': str(row[5]),
        'idempotent': idempotent,
    }


def get_state(*, tenant_id: str) -> dict[str, Any]:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        return _serialized_state(tenant_id, _state_row(cursor, tenant_id))


def get_operation_event(*, tenant_id: str, operation_id: UUID) -> dict[str, Any] | None:
    """Return the immutable replay identity without mutating current state."""
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """SELECT operation,from_state,to_state,actor_ref,target_owner_ref,revision,
                      receipt_digest
                 FROM sitecontent_tenantlifecycleevent
                WHERE site_id=%s AND operation_id=%s""",
            (tenant_id, str(operation_id)),
        )
        row = cursor.fetchone()
    if not row:
        return None
    return {
        'operation': str(row[0]),
        'from': str(row[1]),
        'to': str(row[2]),
        'actor': str(row[3]),
        'targetOwner': str(row[4]),
        'revision': int(row[5]),
        'receiptDigest': str(row[6]),
    }


def provision(
    *, tenant_id: str, owner_ref: str, operation_id: UUID, configuration: dict[str, Any]
) -> dict[str, Any]:
    """Create the one canonical tenant lifecycle record or replay the exact provision."""
    receipt = {
        'tenantId': tenant_id,
        'operation': 'provision',
        'from': 'absent',
        'to': 'provisioning',
        'owner': owner_ref,
        'targetOwner': '',
        'revision': 1,
        'operationId': str(operation_id),
        'configuration': configuration,
    }
    digest = _digest(receipt)
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO sitecontent_tenantlifecyclestate
                     (id,site_id,state,owner_ref,configuration,revision,last_operation_id,
                      last_receipt_digest,created_at,updated_at)
                   VALUES (gen_random_uuid(),%s,'provisioning',%s,%s,1,%s,%s,NOW(),NOW())
                   ON CONFLICT (site_id) DO NOTHING""",
                (tenant_id, owner_ref, json.dumps(configuration), str(operation_id), digest),
            )
            created = cursor.rowcount == 1
            row = _state_row(cursor, tenant_id, lock=True)
            if not created:
                if str(row[4]) != str(operation_id) or str(row[5]) != digest:
                    raise TenantLifecycleRepositoryError('tenant:lifecycle_exists')
                conn.commit()
                return _serialized_state(tenant_id, row, idempotent=True)
            cursor.execute(
                """INSERT INTO sitecontent_tenantlifecycleevent
                     (id,site_id,operation_id,operation,from_state,to_state,actor_ref,
                      target_owner_ref,revision,receipt_digest,created_at,updated_at)
                   VALUES (gen_random_uuid(),%s,%s,'provision','absent','provisioning',
                           %s,'',1,%s,NOW(),NOW())""",
                (tenant_id, str(operation_id), owner_ref, digest),
            )
        conn.commit()
    return _serialized_state(tenant_id, row)


def apply_transition(
    *,
    tenant_id: str,
    current: str,
    target: str,
    owner_ref: str,
    expected_revision: int,
    operation_id: UUID,
    approval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist state, immutable event, and destructive nonce in one transaction."""
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            row = _state_row(cursor, tenant_id, lock=True)
            if not row:
                raise TenantLifecycleRepositoryError('tenant:lifecycle_missing')
            cursor.execute(
                """SELECT operation,from_state,to_state,actor_ref,revision,receipt_digest
                     FROM sitecontent_tenantlifecycleevent
                    WHERE site_id=%s AND operation_id=%s""",
                (tenant_id, str(operation_id)),
            )
            replay = cursor.fetchone()
            if replay:
                if (
                    replay[0] != 'transition'
                    or replay[1] != current
                    or replay[2] != target
                    or replay[3] != owner_ref
                    or int(replay[4]) != expected_revision + 1
                ):
                    raise TenantLifecycleRepositoryError('tenant:operation_conflict')
                conn.commit()
                return _serialized_state(tenant_id, row, idempotent=True)
            if row[0] != current or int(row[3]) != expected_revision or row[1] != owner_ref:
                raise TenantLifecycleRepositoryError('tenant:revision_conflict')
            new_revision = expected_revision + 1
            receipt = {
                'tenantId': tenant_id,
                'operation': 'transition',
                'from': current,
                'to': target,
                'owner': owner_ref,
                'targetOwner': '',
                'revision': new_revision,
                'operationId': str(operation_id),
            }
            digest = _digest(receipt)
            if target in {'deleting', 'deleted'}:
                if not approval:
                    raise TenantLifecycleRepositoryError('tenant:deletion_approval_required')
                cursor.execute(
                    """INSERT INTO sitecontent_destructiveapprovaluse
                         (id,site_id,nonce,approval_digest,expires_at,consumed_at,created_at,updated_at)
                       SELECT gen_random_uuid(),%s,%s,%s,%s,NOW(),NOW(),NOW()
                       WHERE %s>NOW()
                       ON CONFLICT (site_id,nonce) DO NOTHING""",
                    (
                        tenant_id,
                        approval['nonce'],
                        approval['digest'],
                        approval['expiresAt'],
                        approval['expiresAt'],
                    ),
                )
                if cursor.rowcount != 1:
                    raise TenantLifecycleRepositoryError('tenant:deletion_approval_invalid')
            if target != 'active':
                cursor.execute(
                    """UPDATE sitecontent_durablejob
                          SET state='cancelled',lease_owner='',lease_token=NULL,
                              lease_expires_at=NULL,error_code='tenant.not_serving',updated_at=NOW()
                        WHERE site_id=%s AND state IN ('queued','retry','leased')""",
                    (tenant_id,),
                )
                cursor.execute(
                    """UPDATE sitecontent_durableschedule
                          SET enabled=FALSE,claim_token=NULL,claim_expires_at=NULL,updated_at=NOW()
                        WHERE site_id=%s AND enabled=TRUE""",
                    (tenant_id,),
                )
                # Refresh tokens are user-global, not tenant-scoped. Revoking them
                # here would terminate access to unrelated active tenants. Request
                # and job admission already fail closed on this tenant's lifecycle.
            cursor.execute(
                """UPDATE sitecontent_tenantlifecyclestate
                      SET state=%s,revision=%s,last_operation_id=%s,last_receipt_digest=%s,
                          updated_at=NOW()
                    WHERE site_id=%s AND state=%s AND revision=%s""",
                (
                    target,
                    new_revision,
                    str(operation_id),
                    digest,
                    tenant_id,
                    current,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise TenantLifecycleRepositoryError('tenant:revision_conflict')
            cursor.execute(
                """INSERT INTO sitecontent_tenantlifecycleevent
                     (id,site_id,operation_id,operation,from_state,to_state,actor_ref,
                      target_owner_ref,revision,receipt_digest,created_at,updated_at)
                   VALUES (gen_random_uuid(),%s,%s,'transition',%s,%s,%s,'',%s,%s,NOW(),NOW())""",
                (
                    tenant_id,
                    str(operation_id),
                    current,
                    target,
                    owner_ref,
                    new_revision,
                    digest,
                ),
            )
            updated = _state_row(cursor, tenant_id)
        conn.commit()
    return _serialized_state(tenant_id, updated)


def apply_operation(
    *,
    tenant_id: str,
    operation: str,
    owner_ref: str,
    target_owner_ref: str,
    configuration: dict[str, Any] | None,
    expected_revision: int,
    operation_id: UUID,
) -> dict[str, Any]:
    """Persist configure, transfer, or export with optimistic revision and replay safety."""
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            row = _state_row(cursor, tenant_id, lock=True)
            if not row:
                raise TenantLifecycleRepositoryError('tenant:lifecycle_missing')
            cursor.execute(
                """SELECT operation,actor_ref,target_owner_ref,revision,from_state,to_state,
                          receipt_digest
                     FROM sitecontent_tenantlifecycleevent
                    WHERE site_id=%s AND operation_id=%s""",
                (tenant_id, str(operation_id)),
            )
            replay = cursor.fetchone()
            if replay:
                replay_receipt = {
                    'tenantId': tenant_id,
                    'operation': operation,
                    'from': replay[4],
                    'to': replay[5],
                    'owner': owner_ref,
                    'targetOwner': target_owner_ref,
                    'revision': expected_revision + 1,
                    'operationId': str(operation_id),
                    'configuration': configuration if operation == 'configure' else {},
                }
                if (
                    replay[:3] != (operation, owner_ref, target_owner_ref)
                    or int(replay[3]) != expected_revision + 1
                    or str(replay[6]) != _digest(replay_receipt)
                ):
                    raise TenantLifecycleRepositoryError('tenant:operation_conflict')
                conn.commit()
                return _serialized_state(tenant_id, row, idempotent=True)
            if (
                int(row[3]) != expected_revision
                or (operation != 'transfer_accept' and row[1] != owner_ref)
                or row[0] == 'deleted'
            ):
                raise TenantLifecycleRepositoryError('tenant:revision_conflict')
            new_revision = expected_revision + 1
            current_configuration = dict(row[2] or {})
            next_owner = owner_ref
            next_configuration = (
                configuration if operation == 'configure' else current_configuration
            )
            if operation == 'transfer_prepare':
                cursor.execute("SELECT NOW() + INTERVAL '15 minutes'")
                transfer_expires = cursor.fetchone()[0]
                next_configuration = {
                    **current_configuration,
                    '_pendingOwnershipTransfer': {
                        'targetOwner': target_owner_ref,
                        'preparedBy': owner_ref,
                        'operationId': str(operation_id),
                        'expiresAt': transfer_expires.isoformat(),
                    },
                }
            elif operation == 'transfer_accept':
                pending = current_configuration.get('_pendingOwnershipTransfer')
                cursor.execute('SELECT NOW()')
                database_now = cursor.fetchone()[0]
                if not isinstance(pending, dict):
                    raise TenantLifecycleRepositoryError('tenant:transfer_acceptance_invalid')
                try:
                    transfer_expiry = datetime.fromisoformat(str(pending.get('expiresAt')))
                except (AttributeError, ValueError, TypeError) as exc:
                    raise TenantLifecycleRepositoryError(
                        'tenant:transfer_acceptance_invalid'
                    ) from exc
                if (
                    pending.get('targetOwner') != owner_ref
                    or transfer_expiry.tzinfo is None
                    or transfer_expiry <= database_now
                ):
                    raise TenantLifecycleRepositoryError('tenant:transfer_acceptance_invalid')
                next_owner = owner_ref
                # Keep lifecycle ownership and authorization ownership in one
                # transaction so neither the old nor new owner is stranded.
                cursor.execute(
                    """SELECT organization.id
                         FROM api_identity_organizations organization
                         JOIN api_identity_memberships target
                           ON target.organization_id=organization.id
                        WHERE organization.tenant_id=%s
                          AND target.user_id=%s
                          AND target.status='active'
                          AND target.role IN ('owner','admin')
                        FOR UPDATE""",
                    (tenant_id, owner_ref),
                )
                organization = cursor.fetchone()
                if not organization:
                    raise TenantLifecycleRepositoryError('tenant:target_owner_not_administrator')
                cursor.execute(
                    """UPDATE api_identity_memberships
                          SET role=CASE
                            WHEN user_id=%s THEN 'owner'
                            WHEN user_id=%s AND role='owner' THEN 'admin'
                            ELSE role END,
                              updated_at=NOW()
                        WHERE organization_id=%s AND user_id IN (%s,%s)""",
                    (owner_ref, row[1], str(organization[0]), owner_ref, row[1]),
                )
                if cursor.rowcount != 2:
                    raise TenantLifecycleRepositoryError('tenant:ownership_membership_incomplete')
                next_configuration = {
                    key: value
                    for key, value in current_configuration.items()
                    if key != '_pendingOwnershipTransfer'
                }
            receipt = {
                'tenantId': tenant_id,
                'operation': operation,
                'from': row[0],
                'to': row[0],
                'owner': owner_ref,
                'targetOwner': target_owner_ref,
                'revision': new_revision,
                'operationId': str(operation_id),
                'configuration': next_configuration if operation == 'configure' else {},
            }
            digest = _digest(receipt)
            cursor.execute(
                """UPDATE sitecontent_tenantlifecyclestate
                      SET owner_ref=%s,configuration=%s,revision=%s,last_operation_id=%s,
                          last_receipt_digest=%s,updated_at=NOW()
                    WHERE site_id=%s AND revision=%s""",
                (
                    next_owner,
                    json.dumps(next_configuration),
                    new_revision,
                    str(operation_id),
                    digest,
                    tenant_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise TenantLifecycleRepositoryError('tenant:revision_conflict')
            cursor.execute(
                """INSERT INTO sitecontent_tenantlifecycleevent
                     (id,site_id,operation_id,operation,from_state,to_state,actor_ref,
                      target_owner_ref,revision,receipt_digest,created_at,updated_at)
                   VALUES (gen_random_uuid(),%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())""",
                (
                    tenant_id,
                    str(operation_id),
                    operation,
                    row[0],
                    row[0],
                    owner_ref,
                    target_owner_ref,
                    new_revision,
                    digest,
                ),
            )
            updated = _state_row(cursor, tenant_id)
        conn.commit()
    return _serialized_state(tenant_id, updated)


def consume_destructive_approval_nonce(
    tenant_id: str,
    nonce: str,
    approval_digest: str,
    expires_at: datetime,
) -> bool:
    """Atomically consume an approval once, durably and tenant-scoped."""
    if (
        not tenant_id
        or not NONCE.fullmatch(nonce or '')
        or not DIGEST.fullmatch(approval_digest or '')
        or expires_at.tzinfo is None
    ):
        return False
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO sitecontent_destructiveapprovaluse
                     (id,site_id,nonce,approval_digest,expires_at,consumed_at,created_at,updated_at)
                   SELECT gen_random_uuid(),%s,%s,%s,%s,NOW(),NOW(),NOW()
                   WHERE %s>NOW()
                   ON CONFLICT (site_id,nonce) DO NOTHING""",
                (tenant_id, nonce, approval_digest, expires_at, expires_at),
            )
            consumed = cursor.rowcount == 1
        conn.commit()
    return consumed
