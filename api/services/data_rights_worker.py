from __future__ import annotations

import json
import hashlib
from uuid import UUID

from api.db import data_rights_claim_context, db_conn, workspace_db_conn
from api.repositories import data_rights as repository
from api.security.secret_box import SecretBox
from api.services.data_rights import receipt_digest, validate_correction
from api.settings import settings

SUBJECT_DATA_INVENTORY_VERSION = 1
SUBJECT_DATA_INVENTORY = (
    ('sitecontent_contentrevision', 'actor_ref', 'pseudonymize'),
    ('sitecontent_savedview', 'owner_ref', 'delete'),
    ('sitecontent_importjob', 'requester_ref', 'pseudonymize'),
    ('sitecontent_exportjob', 'requester_ref', 'pseudonymize'),
    ('sitecontent_workspaceauditevent', 'actor_ref', 'pseudonymize'),
    ('sitecontent_mediaasset', 'owner_ref', 'media_delete'),
    ('sitecontent_mediauploadsession', 'actor_ref', 'pseudonymize'),
    ('sitecontent_mediametadatarevision', 'actor_ref', 'pseudonymize'),
    ('sitecontent_mediacollection', 'owner_ref', 'pseudonymize'),
    ('sitecontent_mediaretentionhold', 'owner_ref', 'pseudonymize'),
    ('sitecontent_mediadeliverygrant', 'audience_ref', 'pseudonymize'),
    ('sitecontent_mediaauditevent', 'actor_ref', 'pseudonymize'),
    ('sitecontent_mediaauditevent', 'subject_ref', 'pseudonymize'),
    ('sitecontent_mediaabusecase', 'reporter_ref', 'pseudonymize'),
    ('sitecontent_mediaabusecase', 'reviewer_ref', 'pseudonymize'),
    ('sitecontent_mediaabusecase', 'appellant_ref', 'pseudonymize'),
    ('sitecontent_operationsincident', 'owner_ref', 'pseudonymize'),
    ('sitecontent_operationsincidentevent', 'actor_ref', 'pseudonymize'),
    ('sitecontent_tenantlifecyclestate', 'owner_ref', 'pseudonymize'),
    ('sitecontent_tenantlifecycleevent', 'actor_ref', 'pseudonymize'),
    ('sitecontent_tenantlifecycleevent', 'target_owner_ref', 'pseudonymize'),
    ('sitecontent_durablejob', 'owner_ref', 'pseudonymize'),
    ('sitecontent_breakglassgrant', 'requester_ref', 'pseudonymize'),
    ('sitecontent_breakglassgrant', 'approver_ref', 'pseudonymize'),
    ('sitecontent_tenantnotification', 'owner_ref', 'pseudonymize'),
)


def _box() -> SecretBox:
    key = str(settings.IDENTITY_ENCRYPTION_KEY or '').strip()
    if not key:
        raise RuntimeError('identity_encryption_unavailable')
    return SecretBox(key)


def _export_payload(*, tenant_id: str, user_id: UUID) -> dict:
    with db_conn(tenant_id=tenant_id) as conn:
        conn.set_session(isolation_level='REPEATABLE READ', readonly=True)
        with conn.cursor() as cur:
            cur.execute(
                """
            SELECT email, is_active, is_email_verified, display_name, avatar_url, bio, created_at, updated_at
            FROM api_auth_users WHERE id=%s
            """,
                (str(user_id),),
            )
            user = cur.fetchone()
            if not user:
                raise RuntimeError('account_not_found')
            cur.execute(
                """
            SELECT o.tenant_id, o.name, m.role, m.status, m.created_at, m.updated_at
            FROM api_identity_memberships m
            JOIN api_identity_organizations o ON o.id=m.organization_id
            WHERE m.user_id=%s AND o.tenant_id=%s
            """,
                (str(user_id), tenant_id),
            )
            memberships = cur.fetchall() or []
            workspace = _workspace_projection(cur, tenant_id=tenant_id, user_id=user_id)
    return {
        'schema_version': 1,
        'account': {
            'email': user[0],
            'is_active': bool(user[1]),
            'is_email_verified': bool(user[2]),
            'display_name': user[3] or '',
            'avatar_url': user[4] or '',
            'bio': user[5] or '',
            'created_at': user[6].isoformat(),
            'updated_at': user[7].isoformat(),
        },
        'memberships': [
            {
                'tenant_id': row[0],
                'organization_name': row[1],
                'role': row[2],
                'status': row[3],
                'created_at': row[4].isoformat(),
                'updated_at': row[5].isoformat(),
            }
            for row in memberships
        ],
        'workspace': workspace,
    }


def _workspace_projection(cur, *, tenant_id: str, user_id: UUID) -> dict:
    """Project only subject-created records and ordinary-readable typed fields."""
    actor_ref = str(user_id)
    cur.execute(
        """SELECT DISTINCT r.id, r.content_type, r.slug, r.title, r.state,
                          r.schema_version, r.version, r.values, r.definition_id
           FROM sitecontent_contentrecord r
           JOIN sitecontent_workspaceauditevent a
             ON a.site_id=r.site_id AND a.object_type='content_record'
            AND a.object_ref=r.id::text AND a.action='content.create'
           WHERE r.site_id=%s AND a.site_id=%s AND a.actor_ref=%s
           ORDER BY r.id LIMIT 1001""",
        (tenant_id, tenant_id, actor_ref),
    )
    rows = cur.fetchall() or []
    if len(rows) > 1000:
        raise RuntimeError('workspace_privacy_projection_too_large')
    definition_ids = sorted({str(row[8]) for row in rows if row[8]})
    readable: dict[str, set[str]] = {}
    if definition_ids:
        cur.execute(
            """SELECT definition_id, field_key
               FROM sitecontent_contentfielddefinition
               WHERE definition_id=ANY(%s) AND read_permission='content.read'
               ORDER BY definition_id, field_key""",
            (definition_ids,),
        )
        for definition_id, field_key in cur.fetchall() or []:
            readable.setdefault(str(definition_id), set()).add(field_key)
    subject_surfaces = []
    for table, column, treatment in SUBJECT_DATA_INVENTORY:
        if table == 'sitecontent_contentrevision':
            cur.execute(
                f"""SELECT revision.id::text FROM {table} revision
                    JOIN sitecontent_contentrecord content ON content.id=revision.content_id
                    WHERE content.site_id=%s AND revision.{column}=%s
                    ORDER BY revision.id LIMIT 1001""",
                (tenant_id, actor_ref),
            )
        else:
            cur.execute(
                f'SELECT id::text FROM {table} WHERE site_id=%s AND {column}=%s ORDER BY id LIMIT 1001',
                (tenant_id, actor_ref),
            )
        identifiers = [str(item[0]) for item in (cur.fetchall() or [])]
        if len(identifiers) > 1000:
            raise RuntimeError('workspace_subject_inventory_too_large')
        subject_surfaces.append(
            {'table': table, 'column': column, 'treatment': treatment, 'ids': identifiers}
        )
    return {
        'schema_version': 2,
        'subject_inventory_version': SUBJECT_DATA_INVENTORY_VERSION,
        'records': [
            {
                'id': str(row[0]),
                'content_type': row[1],
                'slug': row[2],
                'title': row[3],
                'state': row[4],
                'schema_version': int(row[5]),
                'version': int(row[6]),
                'values': {
                    key: value
                    for key, value in (row[7] if isinstance(row[7], dict) else {}).items()
                    if key in readable.get(str(row[8]), set())
                },
            }
            for row in rows
        ],
        'subject_surfaces': subject_surfaces,
    }


def _workspace_payload(*, tenant_id: str, user_id: UUID) -> dict:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
        return _workspace_projection(cur, tenant_id=tenant_id, user_id=user_id)


def _correct_account(*, tenant_id: str, user_id: UUID, fields: dict) -> UUID:
    assignments: list[str] = []
    values: list[object] = []
    for column in ('display_name', 'avatar_url', 'bio'):
        if column in fields:
            assignments.append(f'{column}=%s')
            values.append(fields[column])
    if not assignments:
        return user_id
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE api_auth_users SET {','.join(assignments)}, updated_at=NOW() "
                "WHERE id=%s AND is_active=TRUE RETURNING id",
                (*values, str(user_id)),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError('account_state_changed')
        conn.commit()
    return UUID(str(row[0]))


def _unlink_workspace_subject(cur, *, tenant_id: str, user_id: UUID) -> None:
    """Erase mutable subject references while retaining business and audit evidence."""
    subject = str(user_id)
    anonymous = 'deleted:' + hashlib.sha256(f'{tenant_id}:{subject}'.encode()).hexdigest()[:24]
    for table, column, treatment in SUBJECT_DATA_INVENTORY:
        if table == 'sitecontent_contentrevision':
            cur.execute(
                f"""UPDATE {table} revision SET {column}=%s
                    FROM sitecontent_contentrecord content
                    WHERE content.id=revision.content_id AND content.site_id=%s
                      AND revision.{column}=%s""",
                (anonymous, tenant_id, subject),
            )
            continue
        if treatment == 'delete':
            cur.execute(
                f'DELETE FROM {table} WHERE site_id=%s AND {column}=%s', (tenant_id, subject)
            )
        elif treatment == 'media_delete':
            cur.execute(
                f"UPDATE {table} SET {column}='', status='deleted', retention_until=NOW(), updated_at=NOW() "
                f'WHERE site_id=%s AND {column}=%s',
                (tenant_id, subject),
            )
        else:
            cur.execute(
                f'UPDATE {table} SET {column}=%s WHERE site_id=%s AND {column}=%s',
                (anonymous, tenant_id, subject),
            )


def _delete_account(*, tenant_id: str, user_id: UUID) -> dict:
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            workspace = _workspace_projection(cur, tenant_id=tenant_id, user_id=user_id)
            _unlink_workspace_subject(cur, tenant_id=tenant_id, user_id=user_id)
            cur.execute(
                'DELETE FROM api_identity_memberships USING api_identity_organizations o WHERE api_identity_memberships.organization_id=o.id AND o.tenant_id=%s AND api_identity_memberships.user_id=%s',
                (tenant_id, str(user_id)),
            )
            cur.execute(
                """SELECT EXISTS (
                       SELECT 1 FROM api_identity_memberships membership
                       WHERE membership.user_id=%s AND membership.status='active'
                   )""",
                (str(user_id),),
            )
            has_other_membership = bool(cur.fetchone()[0])
            if has_other_membership:
                conn.commit()
                return {
                    'schema_version': 2,
                    'tenant_membership_deleted': True,
                    'global_account_deleted': False,
                    'tenant_id': tenant_id,
                    'workspace_records_unlinked': len(workspace['records']),
                }
            cur.execute(
                'UPDATE api_auth_refresh_tokens SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL',
                (str(user_id),),
            )
            cur.execute('DELETE FROM api_identity_recovery_codes WHERE user_id=%s', (str(user_id),))
            cur.execute(
                'DELETE FROM api_identity_login_challenges WHERE user_id=%s', (str(user_id),)
            )
            cur.execute('DELETE FROM api_identity_authenticators WHERE user_id=%s', (str(user_id),))
            cur.execute(
                'UPDATE api_identity_credentials SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL',
                (str(user_id),),
            )
            cur.execute(
                """
                UPDATE api_auth_users
                SET email=%s, password_hash='', is_active=FALSE, is_email_verified=FALSE,
                    display_name='', avatar_url='', bio='', updated_at=NOW()
                WHERE id=%s AND is_active=TRUE
                """,
                (f'deleted-{user_id}@deleted.invalid', str(user_id)),
            )
            if cur.rowcount != 1:
                cur.execute(
                    'SELECT email,is_active FROM api_auth_users WHERE id=%s',
                    (str(user_id),),
                )
                existing = cur.fetchone()
                if existing != (f'deleted-{user_id}@deleted.invalid', False):
                    conn.rollback()
                    raise RuntimeError('account_state_changed')
        conn.commit()
    return {
        'schema_version': 2,
        'tenant_membership_deleted': True,
        'global_account_deleted': True,
        'tenant_id': tenant_id,
        'workspace_records_unlinked': len(workspace['records']),
    }


def _deactivate_account(*, tenant_id: str, user_id: UUID) -> dict:
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT mine.organization_id
                FROM api_identity_memberships mine
                JOIN api_identity_organizations organization
                  ON organization.id=mine.organization_id
                WHERE mine.user_id=%s AND mine.role='owner' AND mine.status='active'
                  AND organization.tenant_id=%s
                  AND NOT EXISTS (
                    SELECT 1 FROM api_identity_memberships other
                    WHERE other.organization_id=mine.organization_id
                      AND other.user_id<>mine.user_id
                      AND other.role='owner' AND other.status='active'
                  )
                LIMIT 1
                """,
                (str(user_id), tenant_id),
            )
            if cur.fetchone():
                conn.rollback()
                raise ValueError('last_owner_required')
            cur.execute(
                """UPDATE api_identity_memberships membership
                      SET status='suspended', updated_at=NOW()
                     FROM api_identity_organizations organization
                    WHERE membership.organization_id=organization.id
                      AND organization.tenant_id=%s AND membership.user_id=%s
                      AND membership.status='active'""",
                (tenant_id, str(user_id)),
            )
            cur.execute(
                """SELECT EXISTS (
                       SELECT 1 FROM api_identity_memberships membership
                       WHERE membership.user_id=%s AND membership.status='active'
                   )""",
                (str(user_id),),
            )
            has_other_membership = bool(cur.fetchone()[0])
            if has_other_membership:
                conn.commit()
                return {
                    'schema_version': 2,
                    'tenant_membership_deactivated': True,
                    'global_account_deactivated': False,
                    'tenant_id': tenant_id,
                }
            cur.execute(
                'UPDATE api_auth_refresh_tokens SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL',
                (str(user_id),),
            )
            cur.execute(
                'UPDATE api_auth_users SET is_active=FALSE, updated_at=NOW() WHERE id=%s AND is_active=TRUE',
                (str(user_id),),
            )
            if cur.rowcount != 1:
                cur.execute('SELECT is_active FROM api_auth_users WHERE id=%s', (str(user_id),))
                existing = cur.fetchone()
                if existing != (False,):
                    conn.rollback()
                    raise RuntimeError('account_state_changed')
        conn.commit()
    return {
        'schema_version': 2,
        'tenant_membership_deactivated': True,
        'global_account_deactivated': True,
        'tenant_id': tenant_id,
    }


def process_operation(operation_id: UUID) -> str:
    operation = repository.claim_operation(operation_id=operation_id)
    if operation is None:
        return 'noop'
    try:
        box = _box()
        request_payload = json.loads(box.decrypt(operation['request_ciphertext']))
        with data_rights_claim_context(str(operation['id']), str(operation['claim_token'])):
            if operation['kind'] == 'export':
                result = _export_payload(
                    tenant_id=operation['tenant_id'], user_id=operation['user_id']
                )
            elif operation['kind'] == 'correction':
                correction = validate_correction(request_payload.get('fields'))
                updated_id = _correct_account(
                    tenant_id=operation['tenant_id'],
                    user_id=operation['user_id'],
                    fields=correction,
                )
                result = {
                    'schema_version': 1,
                    'corrected': sorted(correction),
                    'updated_at': 'committed',
                    'account_id': str(updated_id),
                    'workspace': _workspace_payload(
                        tenant_id=operation['tenant_id'], user_id=operation['user_id']
                    ),
                }
            elif operation['kind'] == 'deletion':
                if request_payload.get('confirmation') != 'DELETE':
                    raise ValueError('deletion_confirmation_invalid')
                result = _delete_account(
                    tenant_id=operation['tenant_id'], user_id=operation['user_id']
                )
            elif operation['kind'] == 'deactivation':
                if request_payload.get('confirmation') != 'DEACTIVATE':
                    raise ValueError('deactivation_confirmation_invalid')
                result = _deactivate_account(
                    tenant_id=operation['tenant_id'], user_id=operation['user_id']
                )
            else:
                raise ValueError('operation_kind_invalid')
        digest = receipt_digest(
            operation_id=str(operation['id']),
            tenant_id=operation['tenant_id'],
            user_id=str(operation['user_id']),
            payload=result,
            key=settings.TOKEN_PEPPER,
        )
        repository.complete_operation(
            operation_id=operation['id'],
            claim_token=operation['claim_token'],
            tenant_id=operation['tenant_id'],
            user_id=operation['user_id'],
            kind=operation['kind'],
            result_ciphertext=box.encrypt(
                json.dumps(result, separators=(',', ':'), sort_keys=True)
            ),
            digest=digest,
        )
        return 'completed'
    except Exception:
        repository.fail_operation(
            operation_id=operation['id'],
            claim_token=operation['claim_token'],
            error_code='processing_failed',
        )
        raise
