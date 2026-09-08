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


def overview(*, tenant_id: str) -> dict[str, Any]:
    """Return the bounded tenant-private operations read model."""
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT service.id, service.service_key, service.environment, service.enabled,
                   service.release_id, sample.state, sample.code, sample.latency_ms,
                   sample.observed_at, sample.expires_at
            FROM sitecontent_operationsservice AS service
            LEFT JOIN LATERAL (
                SELECT state, code, latency_ms, observed_at, expires_at
                FROM sitecontent_operationshealthsample
                WHERE site_id=%s AND service_id=service.id
                ORDER BY observed_at DESC LIMIT 1
            ) AS sample ON TRUE
            WHERE service.site_id=%s
            ORDER BY service.environment, service.service_key
            LIMIT 100
            """,
            (tenant_id, tenant_id),
        )
        services = cursor.fetchall()
        cursor.execute(
            """
            SELECT objective_key, indicator, target, warning_threshold, window_minutes
            FROM sitecontent_operationsobjective
            WHERE site_id=%s ORDER BY objective_key LIMIT 100
            """,
            (tenant_id,),
        )
        objectives = cursor.fetchall()
        cursor.execute(
            """
            SELECT id, journey_key, role, source_commit, status, result_digest,
                   started_at, completed_at
            FROM sitecontent_operationssyntheticrun
            WHERE site_id=%s ORDER BY started_at DESC LIMIT 50
            """,
            (tenant_id,),
        )
        synthetics = cursor.fetchall()
    releases = sorted({str(row[4]) for row in services if row[4]})
    return {
        'site': {'id': tenant_id, 'serviceCount': len(services), 'releaseCount': len(releases)},
        'releases': releases,
        'services': [
            {
                'id': str(row[0]),
                'serviceKey': row[1],
                'environment': row[2],
                'enabled': row[3],
                'releaseId': row[4] or None,
                'health': {
                    'state': row[5] or ('unknown' if row[3] else 'disabled'),
                    'code': row[6] or 'probe.no_evidence',
                    'latencyMs': row[7],
                    'observedAt': row[8],
                    'expiresAt': row[9],
                },
            }
            for row in services
        ],
        'objectives': [
            {
                'objectiveKey': row[0],
                'indicator': row[1],
                'target': float(row[2]),
                'warningThreshold': float(row[3]),
                'windowMinutes': row[4],
            }
            for row in objectives
        ],
        'synthetics': [
            {
                'id': str(row[0]),
                'journeyKey': row[1],
                'role': row[2],
                'sourceCommit': row[3],
                'status': row[4],
                'resultDigest': row[5] or None,
                'startedAt': row[6],
                'completedAt': row[7],
            }
            for row in synthetics
        ],
    }


def incident_detail(*, tenant_id: str, incident_id: UUID) -> dict[str, Any] | None:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, severity, state, summary_code, owner_ref, occurrence_count,
                   first_observed_at, last_observed_at, resolved_at
            FROM sitecontent_operationsincident
            WHERE site_id=%s AND id=%s
            """,
            (tenant_id, str(incident_id)),
        )
        incident = cursor.fetchone()
        if incident is None:
            return None
        cursor.execute(
            """
            SELECT id, event_key, actor_ref, details, occurred_at
            FROM sitecontent_operationsincidentevent
            WHERE site_id=%s AND incident_id=%s
            ORDER BY occurred_at, id LIMIT 200
            """,
            (tenant_id, str(incident_id)),
        )
        events = cursor.fetchall()
    return {
        'id': str(incident[0]),
        'severity': incident[1],
        'state': incident[2],
        'summaryCode': incident[3],
        'ownerRef': incident[4] or None,
        'occurrenceCount': incident[5],
        'firstObservedAt': incident[6],
        'lastObservedAt': incident[7],
        'resolvedAt': incident[8],
        'timeline': [
            {
                'id': str(row[0]),
                'eventKey': row[1],
                'actorRef': row[2],
                'details': row[3],
                'occurredAt': row[4],
            }
            for row in events
        ],
    }


def acknowledge(*, tenant_id: str, incident_id: UUID, owner_ref: str) -> bool:
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
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
        conn.commit()
    return changed


def prune(*, tenant_id: str, batch_size: int = 500) -> dict[str, int]:
    bounded = max(1, min(int(batch_size), 1000))
    policies = {
        'health': ('sitecontent_operationshealthsample', 'created_at', 30),
        'synthetics': ('sitecontent_operationssyntheticrun', 'created_at', 30),
        'incidents': ('sitecontent_operationsincident', 'resolved_at', 365),
    }
    removed: dict[str, int] = {}
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            for label, (table, retention_column, days) in policies.items():
                state = "AND state='resolved'" if label == 'incidents' else ''
                cursor.execute(
                    f"""DELETE FROM {table} WHERE id IN (
                            SELECT id FROM {table}
                            WHERE site_id=%s AND {retention_column} < NOW() - (%s * INTERVAL '1 day')
                            {state} ORDER BY {retention_column} LIMIT %s
                        )""",
                    (tenant_id, days, bounded),
                )
                removed[label] = cursor.rowcount
        conn.commit()
    return removed
