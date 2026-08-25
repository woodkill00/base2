from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from api.db import db_conn
from api.security.identity import is_allowed


def _now() -> datetime:
    return datetime.now(timezone.utc)


def membership(*, user_id: UUID, tenant_id: str) -> dict[str, Any] | None:
    with db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.id, o.tenant_id, o.name, m.role
            FROM api_identity_organizations o
            JOIN api_identity_memberships m ON m.organization_id=o.id
            WHERE o.tenant_id=%s AND m.user_id=%s AND m.status='active'
            """,
            (tenant_id, str(user_id)),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {'organization_id': UUID(str(row[0])), 'tenant_id': row[1], 'name': row[2], 'role': row[3]}


def require_permission(*, user_id: UUID, tenant_id: str, permission: str) -> dict[str, Any]:
    member = membership(user_id=user_id, tenant_id=tenant_id)
    if not member or not is_allowed(member['role'], permission):
        raise PermissionError('not_found')
    return member


def create_totp_authenticator(*, user_id: UUID, ciphertext: str) -> UUID:
    authenticator_id = uuid4()
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM api_identity_authenticators WHERE user_id=%s AND kind='totp' AND is_active=FALSE",
                (str(user_id),),
            )
            cur.execute(
                """
                INSERT INTO api_identity_authenticators
                  (id, user_id, kind, credential_id, secret_ciphertext, is_active)
                VALUES (%s, %s, 'totp', '', %s, FALSE)
                """,
                (str(authenticator_id), str(user_id), ciphertext),
            )
    return authenticator_id


def pending_totp(*, user_id: UUID, authenticator_id: UUID) -> str | None:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT secret_ciphertext
            FROM api_identity_authenticators
            WHERE id=%s AND user_id=%s AND kind='totp' AND is_active=FALSE
              AND created_at > NOW() - INTERVAL '10 minutes'
            """,
            (str(authenticator_id), str(user_id)),
        )
        row = cur.fetchone()
    return str(row[0]) if row else None


def active_totp(*, user_id: UUID) -> dict[str, Any] | None:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, secret_ciphertext
            FROM api_identity_authenticators
            WHERE user_id=%s AND kind='totp' AND is_active=TRUE
            ORDER BY created_at DESC LIMIT 1
            """,
            (str(user_id),),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {'id': UUID(str(row[0])), 'secret_ciphertext': str(row[1])}


def create_login_challenge(
    *, user_id: UUID, token_hash: str, ip: str, user_agent: str, ttl_minutes: int = 5
) -> UUID:
    challenge_id = uuid4()
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM api_identity_login_challenges WHERE user_id=%s AND consumed_at IS NULL",
                (str(user_id),),
            )
            cur.execute(
                """
                INSERT INTO api_identity_login_challenges
                  (id, user_id, token_hash, expires_at, ip, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    str(challenge_id), str(user_id), token_hash,
                    _now() + timedelta(minutes=ttl_minutes), ip or '', user_agent or '',
                ),
            )
    return challenge_id


def pending_login_challenge(*, token_hash: str) -> dict[str, Any] | None:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, ip, user_agent
            FROM api_identity_login_challenges
            WHERE token_hash=%s AND consumed_at IS NULL AND expires_at > NOW()
            """,
            (token_hash,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {'id': UUID(str(row[0])), 'user_id': UUID(str(row[1])), 'ip': row[2], 'user_agent': row[3]}


def consume_login_challenge(*, challenge_id: UUID, user_id: UUID) -> bool:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_identity_login_challenges SET consumed_at=NOW()
                WHERE id=%s AND user_id=%s AND consumed_at IS NULL AND expires_at > NOW()
                """,
                (str(challenge_id), str(user_id)),
            )
            return cur.rowcount == 1


def consume_recovery_code(*, user_id: UUID, code_hash: str) -> bool:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_identity_recovery_codes SET used_at=NOW()
                WHERE user_id=%s AND code_hash=%s AND used_at IS NULL
                """,
                (str(user_id), code_hash),
            )
            return cur.rowcount == 1


def consume_recovery_login(
    *, challenge_id: UUID, user_id: UUID, code_hash: str
) -> bool:
    """Atomically consume a login challenge and exactly one recovery code."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM api_identity_login_challenges
                WHERE id=%s AND user_id=%s AND consumed_at IS NULL AND expires_at > NOW()
                FOR UPDATE
                """,
                (str(challenge_id), str(user_id)),
            )
            if not cur.fetchone():
                conn.rollback()
                return False
            cur.execute(
                """
                UPDATE api_identity_recovery_codes SET used_at=NOW()
                WHERE user_id=%s AND code_hash=%s AND used_at IS NULL
                """,
                (str(user_id), code_hash),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False
            cur.execute(
                "UPDATE api_identity_login_challenges SET consumed_at=NOW() WHERE id=%s AND consumed_at IS NULL",
                (str(challenge_id),),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False
        conn.commit()
    return True


def activate_totp_with_recovery_codes(
    *, user_id: UUID, authenticator_id: UUID, code_hashes: tuple[str, ...]
) -> bool:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_identity_authenticators
                SET is_active=TRUE
                WHERE id=%s AND user_id=%s AND kind='totp' AND is_active=FALSE
                """,
                (str(authenticator_id), str(user_id)),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False
            cur.execute(
                'DELETE FROM api_identity_recovery_codes WHERE user_id=%s', (str(user_id),)
            )
            for code_hash in code_hashes:
                cur.execute(
                    """
                    INSERT INTO api_identity_recovery_codes(id, user_id, code_hash)
                    VALUES (%s, %s, %s)
                    """,
                    (str(uuid4()), str(user_id), code_hash),
                )
        conn.commit()
    return True


def replace_recovery_codes(*, user_id: UUID, code_hashes: tuple[str, ...]) -> None:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM api_identity_authenticators WHERE user_id=%s AND kind='totp' AND is_active=TRUE FOR UPDATE",
                (str(user_id),),
            )
            if not cur.fetchone():
                raise PermissionError('mfa_not_enabled')
            cur.execute(
                'DELETE FROM api_identity_recovery_codes WHERE user_id=%s', (str(user_id),)
            )
            for code_hash in code_hashes:
                cur.execute(
                    "INSERT INTO api_identity_recovery_codes(id, user_id, code_hash) VALUES (%s, %s, %s)",
                    (str(uuid4()), str(user_id), code_hash),
                )
        conn.commit()


def create_invitation(
    *, organization_id: UUID, actor_id: UUID, email: str, role: str, token_hash: str
) -> UUID:
    invitation_id = uuid4()
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_identity_invitations
                  (id, organization_id, email, role, token_hash, expires_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(invitation_id),
                    str(organization_id),
                    email.strip().lower(),
                    role,
                    token_hash,
                    _now() + timedelta(days=7),
                    str(actor_id),
                ),
            )
    return invitation_id


def revoke_invitation(*, organization_id: UUID, invitation_id: UUID) -> bool:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_identity_invitations SET revoked_at=NOW()
                WHERE id=%s AND organization_id=%s AND accepted_at IS NULL AND revoked_at IS NULL
                """,
                (str(invitation_id), str(organization_id)),
            )
            return cur.rowcount == 1


def accept_invitation(
    *, token_hash: str, user_id: UUID, user_email: str, tenant_id: str
) -> dict[str, Any] | None:
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT i.id, i.organization_id, i.role
                FROM api_identity_invitations i
                JOIN api_identity_organizations o ON o.id=i.organization_id
                WHERE i.token_hash=%s AND LOWER(i.email)=LOWER(%s) AND o.tenant_id=%s
                  AND i.accepted_at IS NULL AND i.revoked_at IS NULL AND i.expires_at > NOW()
                FOR UPDATE
                """,
                (token_hash, user_email.strip(), tenant_id),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return None
            invitation_id, organization_id, role = row
            cur.execute(
                """
                INSERT INTO api_identity_memberships(organization_id, user_id, role, status)
                VALUES (%s, %s, %s, 'active')
                ON CONFLICT (organization_id, user_id) DO NOTHING
                """,
                (str(organization_id), str(user_id), role),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return None
            cur.execute(
                "UPDATE api_identity_invitations SET accepted_at=NOW() WHERE id=%s AND accepted_at IS NULL",
                (str(invitation_id),),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return None
        conn.commit()
    return {'organization_id': UUID(str(organization_id)), 'role': str(role)}


def bootstrap_owner_organization(
    *, user_id: UUID, tenant_id: str, name: str
) -> dict[str, Any] | None:
    organization_id = uuid4()
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (f'identity:{tenant_id}',))
            cur.execute('SELECT id FROM api_identity_organizations WHERE tenant_id=%s', (tenant_id,))
            if cur.fetchone():
                conn.rollback()
                return None
            cur.execute(
                'INSERT INTO api_identity_organizations(id, tenant_id, name) VALUES (%s, %s, %s)',
                (str(organization_id), tenant_id, name.strip()),
            )
            cur.execute(
                "INSERT INTO api_identity_memberships(organization_id, user_id, role, status) VALUES (%s, %s, 'owner', 'active')",
                (str(organization_id), str(user_id)),
            )
        conn.commit()
    return {'organization_id': organization_id, 'role': 'owner'}


def create_api_credential(
    *, organization_id: UUID, actor_id: UUID, label: str, prefix: str, secret_hash: str, scopes: list[str]
) -> UUID:
    credential_id = uuid4()
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_identity_credentials
                  (id, organization_id, user_id, label, prefix, secret_hash, scopes)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(credential_id),
                    str(organization_id),
                    str(actor_id),
                    label,
                    prefix,
                    secret_hash,
                    json.dumps(scopes),
                ),
            )
    return credential_id


def revoke_api_credential(*, organization_id: UUID, credential_id: UUID) -> bool:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_identity_credentials SET revoked_at=NOW()
                WHERE id=%s AND organization_id=%s AND revoked_at IS NULL
                """,
                (str(credential_id), str(organization_id)),
            )
            return cur.rowcount == 1


def update_member_role(
    *,
    organization_id: UUID,
    actor_id: UUID,
    member_id: UUID,
    new_role: str,
    expected_updated_at: datetime,
) -> bool:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role FROM api_identity_memberships WHERE organization_id=%s AND user_id=%s AND status='active' FOR UPDATE",
                (str(organization_id), str(actor_id)),
            )
            actor = cur.fetchone()
            if not actor or not is_allowed(str(actor[0]), 'member.manage'):
                conn.rollback()
                raise PermissionError('not_found')
            cur.execute(
                "SELECT role, updated_at FROM api_identity_memberships WHERE organization_id=%s AND user_id=%s AND status='active' FOR UPDATE",
                (str(organization_id), str(member_id)),
            )
            target = cur.fetchone()
            if not target or target[1] != expected_updated_at:
                conn.rollback()
                return False
            if (str(target[0]) == 'owner' or new_role == 'owner') and str(actor[0]) != 'owner':
                conn.rollback()
                raise PermissionError('not_found')
            if str(target[0]) == 'owner' and new_role != 'owner':
                cur.execute(
                    "SELECT COUNT(*) FROM api_identity_memberships WHERE organization_id=%s AND role='owner' AND status='active'",
                    (str(organization_id),),
                )
                if int(cur.fetchone()[0]) <= 1:
                    conn.rollback()
                    raise ValueError('last_owner')
            cur.execute(
                """
                UPDATE api_identity_memberships SET role=%s, updated_at=NOW()
                WHERE organization_id=%s AND user_id=%s AND updated_at=%s
                """,
                (new_role, str(organization_id), str(member_id), expected_updated_at),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False
        conn.commit()
    return True


def admin_overview(*, user_id: UUID, tenant_id: str) -> dict[str, Any]:
    member = require_permission(user_id=user_id, tenant_id=tenant_id, permission='audit.read')
    org_id = member['organization_id']
    with db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id, email, role, expires_at FROM api_identity_invitations
               WHERE organization_id=%s AND accepted_at IS NULL AND revoked_at IS NULL
               AND expires_at > NOW() ORDER BY created_at DESC LIMIT 100""",
            (str(org_id),),
        )
        invitations = [
            {'id': str(row[0]), 'email': row[1], 'role': row[2], 'expires_at': row[3]}
            for row in (cur.fetchall() or [])
        ]
        cur.execute(
            """SELECT u.id, u.email, m.role, m.status, m.updated_at FROM api_identity_memberships m
               JOIN api_auth_users u ON u.id=m.user_id
               WHERE m.organization_id=%s ORDER BY u.email LIMIT 250""",
            (str(org_id),),
        )
        members = [
            {
                'id': str(row[0]), 'email': row[1], 'role': row[2],
                'status': row[3], 'updated_at': row[4],
            }
            for row in (cur.fetchall() or [])
        ]
        cur.execute(
            """SELECT id, label, prefix, scopes, created_at, last_used_at FROM api_identity_credentials
               WHERE organization_id=%s AND revoked_at IS NULL ORDER BY created_at DESC LIMIT 100""",
            (str(org_id),),
        )
        credentials = [
            {
                'id': str(row[0]), 'label': row[1], 'prefix': row[2], 'scopes': row[3],
                'created_at': row[4], 'last_used_at': row[5],
            }
            for row in (cur.fetchall() or [])
        ]
        cur.execute(
            """SELECT id, action, created_at, metadata_json FROM api_auth_audit_events
               WHERE user_id IN (SELECT user_id FROM api_identity_memberships WHERE organization_id=%s)
               ORDER BY created_at DESC LIMIT 100""",
            (str(org_id),),
        )
        audit = [
            {'id': str(row[0]), 'action': row[1], 'created_at': row[2], 'metadata': row[3]}
            for row in (cur.fetchall() or [])
        ]
    return {
        'organization': {'id': str(org_id), 'tenant_id': tenant_id, 'name': member['name']},
        'role': member['role'],
        'invitations': invitations,
        'members': members,
        'credentials': credentials,
        'audit': audit,
        'content': [],
    }
