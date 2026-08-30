from __future__ import annotations

import json
from uuid import UUID

from api.auth.repo import insert_audit_event, update_profile
from api.db import db_conn
from api.repositories import data_rights as repository
from api.security.secret_box import SecretBox
from api.services.data_rights import receipt_digest, validate_correction
from api.settings import settings


def _box() -> SecretBox:
    key = str(settings.IDENTITY_ENCRYPTION_KEY or '').strip()
    if not key:
        raise RuntimeError('identity_encryption_unavailable')
    return SecretBox(key)


def _export_payload(*, tenant_id: str, user_id: UUID) -> dict:
    with db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
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
    return {
        'schema_version': 1,
        'account': {
            'email': user[0], 'is_active': bool(user[1]),
            'is_email_verified': bool(user[2]), 'display_name': user[3] or '',
            'avatar_url': user[4] or '', 'bio': user[5] or '',
            'created_at': user[6].isoformat(), 'updated_at': user[7].isoformat(),
        },
        'memberships': [
            {
                'tenant_id': row[0], 'organization_name': row[1], 'role': row[2],
                'status': row[3], 'created_at': row[4].isoformat(), 'updated_at': row[5].isoformat(),
            }
            for row in memberships
        ],
    }


def _delete_account(*, tenant_id: str, user_id: UUID) -> dict:
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM api_identity_memberships USING api_identity_organizations o WHERE api_identity_memberships.organization_id=o.id AND o.tenant_id=%s AND api_identity_memberships.user_id=%s",
                (tenant_id, str(user_id)),
            )
            cur.execute('UPDATE api_auth_refresh_tokens SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL', (str(user_id),))
            cur.execute('DELETE FROM api_identity_recovery_codes WHERE user_id=%s', (str(user_id),))
            cur.execute('DELETE FROM api_identity_login_challenges WHERE user_id=%s', (str(user_id),))
            cur.execute('DELETE FROM api_identity_authenticators WHERE user_id=%s', (str(user_id),))
            cur.execute('UPDATE api_identity_credentials SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL', (str(user_id),))
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
                conn.rollback()
                raise RuntimeError('account_state_changed')
        conn.commit()
    return {'schema_version': 1, 'deleted': True, 'tenant_id': tenant_id}


def _deactivate_account(*, tenant_id: str, user_id: UUID) -> dict:
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT mine.organization_id
                FROM api_identity_memberships mine
                WHERE mine.user_id=%s AND mine.role='owner' AND mine.status='active'
                  AND NOT EXISTS (
                    SELECT 1 FROM api_identity_memberships other
                    WHERE other.organization_id=mine.organization_id
                      AND other.user_id<>mine.user_id
                      AND other.role='owner' AND other.status='active'
                  )
                LIMIT 1
                """,
                (str(user_id),),
            )
            if cur.fetchone():
                conn.rollback()
                raise ValueError('last_owner_required')
            cur.execute(
                "UPDATE api_auth_refresh_tokens SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL",
                (str(user_id),),
            )
            cur.execute(
                "UPDATE api_identity_memberships SET status='suspended', updated_at=NOW() WHERE user_id=%s AND status='active'",
                (str(user_id),),
            )
            cur.execute(
                "UPDATE api_auth_users SET is_active=FALSE, updated_at=NOW() WHERE id=%s AND is_active=TRUE",
                (str(user_id),),
            )
            if cur.rowcount != 1:
                conn.rollback()
                raise RuntimeError('account_state_changed')
        conn.commit()
    return {'schema_version': 1, 'deactivated': True, 'tenant_id': tenant_id}


def process_operation(operation_id: UUID) -> str:
    operation = repository.claim_operation(operation_id=operation_id)
    if operation is None:
        return 'noop'
    try:
        box = _box()
        request_payload = json.loads(box.decrypt(operation['request_ciphertext']))
        if operation['kind'] == 'export':
            result = _export_payload(
                tenant_id=operation['tenant_id'], user_id=operation['user_id']
            )
        elif operation['kind'] == 'correction':
            correction = validate_correction(request_payload.get('fields'))
            updated = update_profile(
                user_id=operation['user_id'],
                display_name=correction.get('display_name'),
                avatar_url=correction.get('avatar_url'),
                bio=correction.get('bio'),
            )
            result = {
                'schema_version': 1,
                'corrected': sorted(correction),
                'updated_at': 'committed',
                'account_id': str(updated.id),
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
            result_ciphertext=box.encrypt(json.dumps(result, separators=(',', ':'), sort_keys=True)),
            digest=digest,
        )
        insert_audit_event(
            user_id=operation['user_id'],
            action=f"privacy.{operation['kind']}_completed",
            ip='',
            user_agent='',
            metadata={'operation_id': str(operation['id']), 'tenant_id': operation['tenant_id']},
        )
        return 'completed'
    except Exception:
        repository.fail_operation(operation_id=operation['id'], error_code='processing_failed')
        raise
