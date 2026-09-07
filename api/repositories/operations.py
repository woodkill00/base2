"""Tenant-bound PostgreSQL repository for the private operations center."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from api.db import workspace_db_conn


def summary(*, tenant_id: str) -> dict[str, Any]:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT state, COUNT(*)
            FROM sitecontent_operationsincident
            WHERE site_id=%s AND state <> 'resolved'
            GROUP BY state
            """,
            (tenant_id,),
        )
        incidents = {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT COUNT(*) FILTER (WHERE enabled), COUNT(*)
            FROM sitecontent_operationsservice WHERE site_id=%s
            """,
            (tenant_id,),
        )
        service_row = cursor.fetchone() or (0, 0)
        cursor.execute(
            """
            SELECT status, COUNT(*) FROM sitecontent_operationssyntheticrun
            WHERE site_id=%s AND created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY status
            """,
            (tenant_id,),
        )
        synthetics = {str(row[0]): int(row[1]) for row in cursor.fetchall()}
    return {
        'services': {'enabled': int(service_row[0]), 'total': int(service_row[1])},
        'incidents': incidents,
        'synthetics24h': synthetics,
    }


def list_incidents(*, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
    bounded = max(1, min(int(limit), 100))
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, severity, state, summary_code, owner_ref, occurrence_count,
                   first_observed_at, last_observed_at, resolved_at
            FROM sitecontent_operationsincident
            WHERE site_id=%s ORDER BY last_observed_at DESC LIMIT %s
            """,
            (tenant_id, bounded),
        )
        rows = cursor.fetchall()
    return [
        {
            'id': str(row[0]),
            'severity': row[1],
            'state': row[2],
            'summaryCode': row[3],
            'ownerRef': row[4],
            'occurrenceCount': row[5],
            'firstObservedAt': row[6],
            'lastObservedAt': row[7],
            'resolvedAt': row[8],
        }
        for row in rows
    ]


def acknowledge(*, tenant_id: str, incident_id: UUID, owner_ref: str) -> bool:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE sitecontent_operationsincident
            SET state='acknowledged', owner_ref=%s, updated_at=NOW()
            WHERE site_id=%s AND id=%s AND state IN ('firing', 'recurring')
            RETURNING id
            """,
            (owner_ref, tenant_id, str(incident_id)),
        )
        changed = cursor.fetchone() is not None
    return changed
