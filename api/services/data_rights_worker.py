from __future__ import annotations

import json
from uuid import UUID

from api.db import data_rights_claim_context, db_conn, workspace_db_conn
from api.repositories import data_rights as repository
from api.security.secret_box import SecretBox
from api.services.data_rights import receipt_digest, validate_correction
from api.settings import settings

PRIVATE_EXPORT_KEYS = {
    'password_hash',
    'secret_hash',
    'secret_ciphertext',
    'token_hash',
    'code_hash',
    'request_ciphertext',
    'result_ciphertext',
    'claim_token',
    'storage_key',
    'encrypted_object_key',
    'source_object_key',
}
PRIVATE_EXPORT_FRAGMENTS = (
    'password',
    'secret',
    'token',
    'ciphertext',
    'storage_key',
    'object_key',
)


def _privacy_safe_value(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _privacy_safe_value(item)
            for key, item in value.items()
            if str(key).lower() not in PRIVATE_EXPORT_KEYS
            and not any(fragment in str(key).lower() for fragment in PRIVATE_EXPORT_FRAGMENTS)
        }
    if isinstance(value, list):
        return [_privacy_safe_value(item) for item in value]
    return value.isoformat() if hasattr(value, 'isoformat') else value


def _privacy_safe_row(value: object) -> dict:
    if not isinstance(value, dict):
        return {'id': str(value)}
    return {
        str(key): _privacy_safe_value(item)
        for key, item in value.items()
        if str(key).lower() not in PRIVATE_EXPORT_KEYS
    }


def _box() -> SecretBox:
    key = str(settings.IDENTITY_ENCRYPTION_KEY or '').strip()
    if not key:
        raise RuntimeError('identity_encryption_unavailable')
    return SecretBox(key)


def _export_payload(*, tenant_id: str, user_id: UUID) -> dict:
    with (
        db_conn(tenant_id=tenant_id, isolation_level='REPEATABLE READ', readonly=True) as conn,
        conn.cursor() as cur,
    ):
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
        cur.execute(
            """SELECT id,kind,is_active,created_at,last_used_at
                 FROM api_identity_authenticators WHERE user_id=%s ORDER BY created_at,id""",
            (str(user_id),),
        )
        authenticators = cur.fetchall() or []
        cur.execute(
            """SELECT credential.id,credential.label,credential.prefix,credential.scopes,
                      credential.expires_at,credential.revoked_at,credential.created_at,
                      credential.last_used_at
                 FROM api_identity_credentials credential
                 JOIN api_identity_organizations organization
                   ON organization.id=credential.organization_id
                WHERE credential.user_id=%s AND organization.tenant_id=%s
                ORDER BY credential.created_at,credential.id""",
            (str(user_id), tenant_id),
        )
        credentials = cur.fetchall() or []
        cur.execute(
            """SELECT id,action,ip,user_agent,metadata_json,created_at
                 FROM api_auth_audit_events WHERE user_id=%s ORDER BY created_at,id LIMIT 10001""",
            (str(user_id),),
        )
        audit_events = cur.fetchall() or []
        if len(audit_events) > 10000:
            raise RuntimeError('identity_privacy_projection_too_large')
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
        'authenticators': [
            {
                'id': str(row[0]),
                'kind': row[1],
                'is_active': bool(row[2]),
                'created_at': row[3].isoformat(),
                'last_used_at': row[4].isoformat() if row[4] else None,
            }
            for row in authenticators
        ],
        'credentials': [
            {
                'id': str(row[0]),
                'label': row[1],
                'prefix': row[2],
                'scopes': row[3],
                'expires_at': row[4].isoformat() if row[4] else None,
                'revoked_at': row[5].isoformat() if row[5] else None,
                'created_at': row[6].isoformat(),
                'last_used_at': row[7].isoformat() if row[7] else None,
            }
            for row in credentials
        ],
        'audit_events': [
            {
                'id': str(row[0]),
                'action': row[1],
                'ip': row[2],
                'user_agent': row[3],
                'metadata': row[4],
                'created_at': row[5].isoformat(),
            }
            for row in audit_events
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
    cur.execute('SELECT * FROM base2_export_data_rights_subject_surfaces()', ())
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for table, column, treatment, raw_row in cur.fetchall() or []:
        key = (table, column, treatment)
        rows_for_surface = grouped.setdefault(key, [])
        if raw_row is None:
            continue
        if len(rows_for_surface) >= 1000:
            raise RuntimeError('workspace_subject_inventory_too_large')
        rows_for_surface.append(_privacy_safe_row(raw_row))
    subject_surfaces = [
        {
            'table': table,
            'column': column,
            'treatment': treatment,
            'ids': [str(item.get('id', '')) for item in rows],
            'rows': rows,
        }
        for (table, column, treatment), rows in sorted(grouped.items())
    ]
    return {
        'schema_version': 3,
        'subject_inventory_version': 1,
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


def _correct_account(*, operation_id: UUID, claim_token: UUID, user_id: UUID, fields: dict) -> UUID:
    if not fields:
        return user_id
    result = repository.apply_subject_action(
        operation_id=operation_id, claim_token=claim_token, action='correction', fields=fields
    )
    return UUID(str(result['account_id']))


def _delete_account(
    *, operation_id: UUID, claim_token: UUID, tenant_id: str, user_id: UUID
) -> dict:
    workspace = _workspace_payload(tenant_id=tenant_id, user_id=user_id)
    result = repository.apply_subject_action(
        operation_id=operation_id, claim_token=claim_token, action='deletion'
    )
    return {
        'schema_version': 3,
        **result,
        'workspace_records_unlinked': len(workspace['records']),
    }


def _deactivate_account(*, operation_id: UUID, claim_token: UUID) -> dict:
    result = repository.apply_subject_action(
        operation_id=operation_id, claim_token=claim_token, action='deactivation'
    )
    return {'schema_version': 3, **result}


def process_operation(operation_id: UUID, dispatch_token: UUID) -> str:
    operation = repository.claim_operation(operation_id=operation_id, dispatch_token=dispatch_token)
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
                    operation_id=operation['id'],
                    claim_token=operation['claim_token'],
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
                    operation_id=operation['id'],
                    claim_token=operation['claim_token'],
                    tenant_id=operation['tenant_id'],
                    user_id=operation['user_id'],
                )
            elif operation['kind'] == 'deactivation':
                if request_payload.get('confirmation') != 'DEACTIVATE':
                    raise ValueError('deactivation_confirmation_invalid')
                result = _deactivate_account(
                    operation_id=operation['id'], claim_token=operation['claim_token']
                )
            elif operation['kind'] == 'global_deletion':
                if request_payload.get('confirmation') != 'DELETE GLOBAL ACCOUNT':
                    raise ValueError('global_deletion_confirmation_invalid')
                result = repository.apply_subject_action(
                    operation_id=operation['id'],
                    claim_token=operation['claim_token'],
                    action='global_deletion',
                )
            elif operation['kind'] == 'global_deactivation':
                if request_payload.get('confirmation') != 'DEACTIVATE GLOBAL ACCOUNT':
                    raise ValueError('global_deactivation_confirmation_invalid')
                result = repository.apply_subject_action(
                    operation_id=operation['id'],
                    claim_token=operation['claim_token'],
                    action='global_deactivation',
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
