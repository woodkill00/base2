from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from api.db import db_conn


def create_operation(
    *, tenant_id: str, user_id: UUID, kind: str, request_ciphertext: str, retention_days: int = 30
) -> tuple[UUID, bool]:
    operation_id = uuid4()
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_data_rights_operations
                  (id, tenant_id, user_id, kind, request_ciphertext, retention_until)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, user_id, kind)
                  WHERE status IN ('queued', 'running')
                DO NOTHING
                """,
                (
                    str(operation_id),
                    tenant_id,
                    str(user_id),
                    kind,
                    request_ciphertext,
                    datetime.now(timezone.utc) + timedelta(days=max(1, min(retention_days, 90))),
                ),
            )
            created = cur.rowcount == 1
            if not created:
                cur.execute(
                    """
                    SELECT id FROM api_data_rights_operations
                    WHERE tenant_id=%s AND user_id=%s AND kind=%s
                      AND status IN ('queued','running')
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (tenant_id, str(user_id), kind),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError('operation_conflict_unresolved')
                operation_id = UUID(str(row[0]))
        conn.commit()
    return operation_id, created


def owned_operation(*, operation_id: UUID, tenant_id: str, user_id: UUID) -> dict[str, Any] | None:
    with db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, kind, status, request_ciphertext, result_ciphertext, receipt_digest,
                   error_code, created_at, completed_at, retention_until
            FROM api_data_rights_operations
            WHERE id=%s AND tenant_id=%s AND user_id=%s
            """,
            (str(operation_id), tenant_id, str(user_id)),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        'id': UUID(str(row[0])),
        'kind': row[1],
        'status': row[2],
        'request_ciphertext': row[3],
        'result_ciphertext': row[4],
        'receipt_digest': row[5],
        'error_code': row[6],
        'created_at': row[7],
        'completed_at': row[8],
        'retention_until': row[9],
    }


def list_owned_operations(
    *, tenant_id: str, user_id: UUID, limit: int = 50
) -> list[dict[str, Any]]:
    with db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, kind, status, error_code, created_at, completed_at, retention_until
            FROM api_data_rights_operations
            WHERE tenant_id=%s AND user_id=%s
            ORDER BY created_at DESC LIMIT %s
            """,
            (tenant_id, str(user_id), max(1, min(limit, 100))),
        )
        rows = cur.fetchall() or []
    return [
        {
            'id': UUID(str(row[0])),
            'kind': row[1],
            'status': row[2],
            'error_code': row[3],
            'created_at': row[4],
            'completed_at': row[5],
            'retention_until': row[6],
        }
        for row in rows
    ]


def list_tenant_operations(*, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, kind, status, error_code, created_at, completed_at, retention_until
            FROM api_data_rights_operations
            WHERE tenant_id=%s
            ORDER BY created_at DESC LIMIT %s
            """,
            (tenant_id, max(1, min(limit, 200))),
        )
        rows = cur.fetchall() or []
    return [
        {
            'id': UUID(str(row[0])),
            'user_id': UUID(str(row[1])),
            'kind': row[2],
            'status': row[3],
            'error_code': row[4],
            'created_at': row[5],
            'completed_at': row[6],
            'retention_until': row[7],
        }
        for row in rows
    ]


def queued_operation_ids(*, limit: int = 25) -> list[tuple[UUID, UUID]]:
    with db_conn() as conn:
        with conn.cursor() as cur:  # noqa: SIM117 - close cursor before committing dispatch leases
            cur.execute(
                'SELECT id,dispatch_token FROM base2_list_due_data_rights_operations(%s)',
                (max(1, min(limit, 100)),),
            )
            operations = [(UUID(str(row[0])), UUID(str(row[1]))) for row in (cur.fetchall() or [])]
        conn.commit()
    return operations


def claim_operation(*, operation_id: UUID, dispatch_token: UUID) -> dict[str, Any] | None:
    claim_token = uuid4()
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT * FROM base2_claim_data_rights_operation(%s,%s,%s)',
                (str(operation_id), str(dispatch_token), str(claim_token)),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return None
        conn.commit()
    return {
        'id': UUID(str(row[0])),
        'tenant_id': row[1],
        'user_id': UUID(str(row[2])),
        'kind': row[3],
        'request_ciphertext': row[4],
        'claim_token': UUID(str(row[5])),
    }


def complete_operation(
    *,
    operation_id: UUID,
    claim_token: UUID,
    tenant_id: str,
    user_id: UUID,
    kind: str,
    result_ciphertext: str,
    digest: str,
) -> None:
    with db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT base2_finalize_data_rights_operation(%s,%s,'completed',%s,%s,'',%s,%s,%s)",
                (
                    str(operation_id),
                    str(claim_token),
                    result_ciphertext,
                    digest,
                    tenant_id,
                    str(user_id),
                    kind,
                ),
            )
            row = cur.fetchone()
            if not row or row[0] is not True:
                raise RuntimeError('operation_state_changed')
        conn.commit()


def fail_operation(*, operation_id: UUID, claim_token: UUID, error_code: str) -> None:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "SELECT base2_finalize_data_rights_operation(%s,%s,'failed','','',%s,'','00000000-0000-0000-0000-000000000000','')",
                (str(operation_id), str(claim_token), error_code[:80]),
            )


def apply_subject_action(
    *, operation_id: UUID, claim_token: UUID, action: str, fields: dict[str, Any] | None = None
) -> dict[str, Any]:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT base2_apply_data_rights_subject_action(%s,%s,%s,%s::jsonb)',
                (str(operation_id), str(claim_token), action, json.dumps(fields or {})),
            )
            row = cur.fetchone()
            if not row or not isinstance(row[0], dict):
                raise RuntimeError('operation_state_changed')
        conn.commit()
    return row[0]


def expire_results() -> int:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute('SELECT base2_expire_data_rights_results()')
            row = cur.fetchone()
            return int(row[0] if row else 0)
