"""Atomic PostgreSQL quota reservations scoped by the tenant RLS context."""

from __future__ import annotations

from typing import Any

from api.db import workspace_db_conn


class QuotaRepositoryError(ValueError):
    pass


def list_quotas(*, tenant_id: str) -> list[dict[str, Any]]:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            'SELECT quota_key, "limit", used, reserved, revision '
            'FROM sitecontent_tenantquota WHERE site_id=%s ORDER BY quota_key',
            (tenant_id,),
        )
        rows = cursor.fetchall()
    return [
        {
            'quotaKey': row[0],
            'limit': int(row[1]),
            'used': int(row[2]),
            'reserved': int(row[3]),
            'available': int(row[1]) - int(row[2]) - int(row[3]),
            'revision': int(row[4]),
        }
        for row in rows
    ]


def reserve(*, tenant_id: str, quota_key: str, amount: int, reservation_id: str) -> dict[str, Any]:
    if amount < 1:
        raise QuotaRepositoryError('quota:amount_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            # Serialize the idempotency key before checking it. Row locking alone
            # cannot lock an absent row and would allow two first-use requests to
            # race into the unique constraint instead of producing an exact replay.
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f'{tenant_id}:{reservation_id}',),
            )
            cursor.execute(
                """SELECT reservation.quota_id, quota.quota_key, reservation.amount,
                          reservation.state
                   FROM sitecontent_tenantquotareservation AS reservation
                   JOIN sitecontent_tenantquota AS quota ON quota.site_id=reservation.site_id
                        AND quota.id=reservation.quota_id
                   WHERE reservation.site_id=%s AND reservation.reservation_id=%s
                   FOR UPDATE OF reservation""",
                (tenant_id, reservation_id),
            )
            prior = cursor.fetchone()
            if prior:
                if prior[1] != quota_key or int(prior[2]) != amount:
                    raise QuotaRepositoryError('quota:reservation_conflict')
                return {'status': prior[3], 'reservationId': reservation_id, 'replayed': True}
            cursor.execute(
                """SELECT id, "limit", used, reserved FROM sitecontent_tenantquota
                   WHERE site_id=%s AND quota_key=%s FOR UPDATE""",
                (tenant_id, quota_key),
            )
            quota = cursor.fetchone()
            if not quota:
                raise QuotaRepositoryError('quota:not_configured')
            if int(quota[2]) + int(quota[3]) + amount > int(quota[1]):
                raise QuotaRepositoryError('quota:exhausted')
            cursor.execute(
                """INSERT INTO sitecontent_tenantquotareservation
                   (id, site_id, reservation_id, amount, state, quota_id, created_at, updated_at)
                   VALUES (gen_random_uuid(), %s, %s, %s, 'reserved', %s, NOW(), NOW())""",
                (tenant_id, reservation_id, amount, str(quota[0])),
            )
            cursor.execute(
                """UPDATE sitecontent_tenantquota SET reserved=reserved+%s,
                          revision=revision+1, updated_at=NOW()
                   WHERE site_id=%s AND id=%s""",
                (amount, tenant_id, str(quota[0])),
            )
        conn.commit()
    return {'status': 'reserved', 'reservationId': reservation_id, 'replayed': False}


def settle(*, tenant_id: str, reservation_id: str, commit: bool) -> dict[str, Any]:
    target = 'committed' if commit else 'released'
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT reservation.quota_id, reservation.amount, reservation.state
                   FROM sitecontent_tenantquotareservation AS reservation
                   WHERE reservation.site_id=%s AND reservation.reservation_id=%s
                   FOR UPDATE""",
                (tenant_id, reservation_id),
            )
            row = cursor.fetchone()
            if not row:
                raise QuotaRepositoryError('quota:reservation_not_found')
            if row[2] != 'reserved':
                if row[2] == target:
                    return {'status': target, 'reservationId': reservation_id, 'replayed': True}
                raise QuotaRepositoryError('quota:settlement_conflict')
            used = 'used=used+%s,' if commit else ''
            parameters = (
                (int(row[1]), int(row[1]), tenant_id, str(row[0]))
                if commit
                else (int(row[1]), tenant_id, str(row[0]))
            )
            cursor.execute(
                f"""UPDATE sitecontent_tenantquota SET {used} reserved=reserved-%s,
                           revision=revision+1, updated_at=NOW()
                    WHERE site_id=%s AND id=%s""",
                parameters,
            )
            cursor.execute(
                """UPDATE sitecontent_tenantquotareservation SET state=%s, updated_at=NOW()
                   WHERE site_id=%s AND reservation_id=%s""",
                (target, tenant_id, reservation_id),
            )
        conn.commit()
    return {'status': target, 'reservationId': reservation_id, 'replayed': False}
