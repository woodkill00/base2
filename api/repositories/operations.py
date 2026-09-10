"""Tenant-bound PostgreSQL repository for the private operations center."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from api.db import workspace_db_conn
from api.services.operations_center import incident_fingerprint


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
            SELECT id, environment, severity, state, summary_code, owner_ref, occurrence_count,
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
            'environment': row[1],
            'severity': row[2],
            'state': row[3],
            'summaryCode': row[4],
            'ownerRef': row[5],
            'occurrenceCount': row[6],
            'firstObservedAt': row[7],
            'lastObservedAt': row[8],
            'resolvedAt': row[9],
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
        cursor.execute(
            """SELECT
                   COUNT(*) FILTER (WHERE state IN ('queued','retry')),
                   COUNT(*) FILTER (WHERE state='leased'),
                   COUNT(*) FILTER (WHERE state='dead_letter')
               FROM sitecontent_durablejob WHERE site_id=%s""",
            (tenant_id,),
        )
        jobs = cursor.fetchone() or (0, 0, 0)
        cursor.execute(
            """SELECT COUNT(*) FILTER (WHERE enabled),
                      COUNT(*) FILTER (WHERE enabled AND next_run_at < NOW())
               FROM sitecontent_durableschedule WHERE site_id=%s""",
            (tenant_id,),
        )
        schedules = cursor.fetchone() or (0, 0)
        cursor.execute(
            """SELECT COUNT(*) FILTER (WHERE status IN ('queued','sending')),
                      COUNT(*) FILTER (WHERE status IN ('failed','expired'))
               FROM sitecontent_operationsalertdelivery WHERE site_id=%s""",
            (tenant_id,),
        )
        alerts = cursor.fetchone() or (0, 0)
        cursor.execute(
            """SELECT id,job_type,error_code,attempts,maximum_attempts,updated_at
               FROM sitecontent_durablejob
               WHERE site_id=%s AND state='dead_letter'
               ORDER BY updated_at DESC,id LIMIT 25""",
            (tenant_id,),
        )
        dead_letters = cursor.fetchall()
        cursor.execute(
            """SELECT id,schedule_key,job_type,timezone,rule,missed_policy,overlap_policy,
                      enabled,next_run_at,last_run_at
               FROM sitecontent_durableschedule WHERE site_id=%s
               ORDER BY schedule_key,id LIMIT 25""",
            (tenant_id,),
        )
        schedule_details = cursor.fetchall()
        cursor.execute(
            """SELECT id,status,attempts,maximum_attempts,next_attempt_at,error_code,
                      created_at,updated_at
               FROM sitecontent_operationsalertdelivery WHERE site_id=%s
               ORDER BY updated_at DESC,id LIMIT 25""",
            (tenant_id,),
        )
        alert_details = cursor.fetchall()
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
        'runtime': {
            'jobs': {
                'ready': int(jobs[0]),
                'leased': int(jobs[1]),
                'deadLetters': int(jobs[2]),
                'items': [
                    {
                        'jobId': str(row[0]),
                        'jobType': row[1],
                        'errorCode': row[2],
                        'attempts': row[3],
                        'maximumAttempts': row[4],
                        'updatedAt': row[5],
                    }
                    for row in dead_letters
                ],
            },
            'schedules': {
                'enabled': int(schedules[0]),
                'late': int(schedules[1]),
                'items': [
                    {
                        'scheduleId': str(row[0]),
                        'scheduleKey': row[1],
                        'jobType': row[2],
                        'timezone': row[3],
                        'rule': row[4],
                        'missedPolicy': row[5],
                        'overlapPolicy': row[6],
                        'enabled': row[7],
                        'nextRunAt': row[8],
                        'lastRunAt': row[9],
                    }
                    for row in schedule_details
                ],
            },
            'alerts': {
                'pending': int(alerts[0]),
                'terminal': int(alerts[1]),
                'items': [
                    {
                        'deliveryId': str(row[0]),
                        'status': row[1],
                        'attempts': row[2],
                        'maximumAttempts': row[3],
                        'nextAttemptAt': row[4],
                        'errorCode': row[5] or None,
                        'createdAt': row[6],
                        'updatedAt': row[7],
                    }
                    for row in alert_details
                ],
            },
        },
    }


def incident_detail(*, tenant_id: str, incident_id: UUID) -> dict[str, Any] | None:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, environment, severity, state, summary_code, owner_ref, occurrence_count,
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
        'environment': incident[1],
        'severity': incident[2],
        'state': incident[3],
        'summaryCode': incident[4],
        'ownerRef': incident[5] or None,
        'occurrenceCount': incident[6],
        'firstObservedAt': incident[7],
        'lastObservedAt': incident[8],
        'resolvedAt': incident[9],
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


def record_probe_batch(
    *, tenant_id: str, environment: str, results: list[dict[str, Any]], now: datetime
) -> dict[str, int]:
    """Persist one bounded probe batch and correlate incident transitions atomically."""
    if environment not in {'preview', 'staging', 'production'} or now.tzinfo is None:
        raise ValueError('operations:collection_scope_invalid')
    if not isinstance(results, list) or len(results) > 32:
        raise ValueError('operations:collection_batch_invalid')
    counters = {'samples': 0, 'opened': 0, 'resolved': 0, 'alerts': 0}
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            for item in results:
                probe_id = str(item['probeId'])
                state = str(item['state'])
                code = str(item['code'])
                observed_at = datetime.fromisoformat(str(item['observedAt']))
                expires_at = datetime.fromisoformat(str(item['expiresAt']))
                latency = item.get('latencyMs')
                service_id = uuid4()
                cursor.execute(
                    """INSERT INTO sitecontent_operationsservice
                       (id,site_id,service_key,environment,enabled,release_id,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,true,'',%s,%s)
                       ON CONFLICT (site_id,environment,service_key) DO UPDATE
                       SET enabled=true,updated_at=EXCLUDED.updated_at RETURNING id""",
                    (str(service_id), tenant_id, probe_id, environment, now, now),
                )
                service_id = cursor.fetchone()[0]
                cursor.execute(
                    """INSERT INTO sitecontent_operationshealthsample
                       (id,site_id,service_id,state,code,latency_ms,dimensions,
                        observed_at,expires_at,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,'{}',%s,%s,%s,%s)""",
                    (
                        str(uuid4()),
                        tenant_id,
                        str(service_id),
                        state,
                        code,
                        latency,
                        observed_at,
                        expires_at,
                        now,
                        now,
                    ),
                )
                counters['samples'] += 1
                if state == 'healthy':
                    cursor.execute(
                        """SELECT incident.id
                           FROM sitecontent_operationsincident AS incident
                           WHERE incident.site_id=%s AND incident.environment=%s
                             AND incident.state <> 'resolved'
                             AND EXISTS (
                                 SELECT 1 FROM sitecontent_operationsincidentevent AS event
                                 WHERE event.site_id=incident.site_id
                                   AND event.incident_id=incident.id
                                   AND event.details->>'service-key'=%s
                             )
                           FOR UPDATE OF incident""",
                        (tenant_id, environment, probe_id),
                    )
                    for (incident_id,) in cursor.fetchall():
                        cursor.execute(
                            """UPDATE sitecontent_operationsincident
                               SET state='resolved',resolved_at=%s,last_observed_at=%s,updated_at=%s
                               WHERE site_id=%s AND id=%s""",
                            (now, now, now, tenant_id, str(incident_id)),
                        )
                        cursor.execute(
                            """INSERT INTO sitecontent_operationsincidentevent
                               (id,site_id,incident_id,event_key,actor_ref,details,
                                occurred_at,created_at,updated_at)
                               VALUES (%s,%s,%s,'incident.resolved','system',%s,%s,%s,%s)""",
                            (
                                str(uuid4()),
                                tenant_id,
                                str(incident_id),
                                json.dumps({'service-key': probe_id, 'environment': environment}),
                                now,
                                now,
                                now,
                            ),
                        )
                        counters['resolved'] += 1
                    continue
                fingerprint = incident_fingerprint(
                    site_id=tenant_id,
                    environment=environment,
                    service_key=probe_id,
                    code=code,
                )
                cursor.execute(
                    'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                    (f'{tenant_id}:{environment}:{fingerprint}',),
                )
                cursor.execute(
                    """SELECT id,state,occurrence_count
                       FROM sitecontent_operationsincident
                       WHERE site_id=%s AND environment=%s AND fingerprint=%s FOR UPDATE""",
                    (tenant_id, environment, fingerprint),
                )
                prior = cursor.fetchone()
                transition = prior is None or prior[1] == 'resolved'
                severity = 'high' if state == 'unavailable' else 'warning'
                if prior is None:
                    incident_id = uuid4()
                    occurrence = 1
                    incident_state = 'firing'
                    cursor.execute(
                        """INSERT INTO sitecontent_operationsincident
                           (id,site_id,fingerprint,environment,severity,state,summary_code,owner_ref,
                            occurrence_count,first_observed_at,last_observed_at,resolved_at,
                            created_at,updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,'',%s,%s,%s,NULL,%s,%s)""",
                        (
                            str(incident_id),
                            tenant_id,
                            fingerprint,
                            environment,
                            severity,
                            incident_state,
                            code,
                            occurrence,
                            now,
                            now,
                            now,
                            now,
                        ),
                    )
                else:
                    incident_id = prior[0]
                    occurrence = int(prior[2]) + 1
                    incident_state = 'recurring' if prior[1] == 'resolved' else prior[1]
                    cursor.execute(
                        """UPDATE sitecontent_operationsincident
                           SET state=%s,severity=%s,occurrence_count=%s,last_observed_at=%s,
                               resolved_at=NULL,updated_at=%s
                           WHERE site_id=%s AND id=%s""",
                        (
                            incident_state,
                            severity,
                            occurrence,
                            now,
                            now,
                            tenant_id,
                            str(incident_id),
                        ),
                    )
                cursor.execute(
                    """INSERT INTO sitecontent_operationsincidentevent
                       (id,site_id,incident_id,event_key,actor_ref,details,
                        occurred_at,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,'system',%s,%s,%s,%s)""",
                    (
                        str(uuid4()),
                        tenant_id,
                        str(incident_id),
                        'incident.opened' if prior is None else 'incident.observed',
                        json.dumps({'service-key': probe_id, 'environment': environment}),
                        now,
                        now,
                        now,
                    ),
                )
                if transition and severity in {'high', 'critical'}:
                    cursor.execute(
                        """INSERT INTO sitecontent_operationsalertdelivery
                           (id,site_id,incident_id,channel,generation,status,attempts,
                            maximum_attempts,next_attempt_at,expires_at,receipt_digest,error_code,
                            created_at,updated_at)
                           VALUES (%s,%s,%s,'discord',%s,'queued',0,5,%s,%s,'','',%s,%s)
                           ON CONFLICT (site_id,incident_id,channel,generation) DO NOTHING""",
                        (
                            str(uuid4()),
                            tenant_id,
                            str(incident_id),
                            occurrence,
                            now,
                            now + timedelta(minutes=15),
                            now,
                            now,
                        ),
                    )
                    counters['alerts'] += cursor.rowcount
                if transition:
                    counters['opened'] += 1
        conn.commit()
    return counters


def claim_alert_deliveries(
    *, tenant_id: str, now: datetime, limit: int = 25
) -> list[dict[str, Any]]:
    bounded = max(1, min(int(limit), 50))
    claim_token = uuid4()
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """WITH candidates AS (
                       SELECT delivery.id
                       FROM sitecontent_operationsalertdelivery AS delivery
                       WHERE delivery.site_id=%s
                         AND (delivery.status='queued' OR
                              (delivery.status='sending' AND delivery.claim_expires_at<=%s))
                         AND delivery.next_attempt_at<=%s
                       ORDER BY delivery.next_attempt_at,delivery.id
                       FOR UPDATE SKIP LOCKED LIMIT %s
                   )
                   UPDATE sitecontent_operationsalertdelivery AS delivery
                   SET status='sending',claim_token=%s,claim_expires_at=%s,updated_at=NOW()
                   FROM candidates,sitecontent_operationsincident AS incident
                   WHERE delivery.id=candidates.id AND incident.site_id=delivery.site_id
                     AND incident.id=delivery.incident_id
                   RETURNING delivery.id,delivery.attempts,delivery.maximum_attempts,
                     delivery.expires_at,incident.fingerprint,incident.severity,
                     incident.summary_code,delivery.claim_token""",
                (tenant_id, now, now, bounded, str(claim_token), now + timedelta(minutes=2)),
            )
            rows = cursor.fetchall()
        conn.commit()
    return [
        {
            'deliveryId': str(row[0]),
            'attempts': int(row[1]),
            'maximumAttempts': int(row[2]),
            'expiresAt': row[3],
            'incidentFingerprint': row[4],
            'severity': row[5],
            'summaryCode': row[6],
            'claimToken': str(row[7]),
        }
        for row in rows
    ]


def due_alert_deliveries(*, tenant_id: str, now: datetime, limit: int = 25) -> list[dict[str, Any]]:
    """Compatibility entry point; claiming is intentionally state-changing."""
    return claim_alert_deliveries(tenant_id=tenant_id, now=now, limit=limit)


def update_alert_delivery(
    *,
    tenant_id: str,
    delivery_id: UUID,
    claim_token: UUID,
    status: str,
    next_attempt_at: datetime | None,
    receipt_digest: str = '',
    error_code: str = '',
) -> bool:
    if status not in {'queued', 'sent', 'failed', 'expired'}:
        raise ValueError('operations:delivery_state_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE sitecontent_operationsalertdelivery
                   SET attempts=attempts+1,status=%s,next_attempt_at=COALESCE(%s,next_attempt_at),
                       receipt_digest=%s,error_code=%s,claim_token=NULL,claim_expires_at=NULL,
                       updated_at=NOW()
                   WHERE site_id=%s AND id=%s AND status='sending' AND claim_token=%s
                   RETURNING id""",
                (
                    status,
                    next_attempt_at,
                    receipt_digest,
                    error_code,
                    tenant_id,
                    str(delivery_id),
                    str(claim_token),
                ),
            )
            changed = cursor.fetchone() is not None
        conn.commit()
    return changed
