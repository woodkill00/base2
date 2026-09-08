"""Tenant-scoped durable job, dead-letter, and scheduler repository."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api.db import workspace_db_conn


class RuntimeRepositoryError(ValueError):
    pass


IDENTIFIER = re.compile(r'^[a-z][a-z0-9_.:-]{2,127}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')


def enqueue_job(
    *,
    tenant_id: str,
    owner_ref: str,
    job_type: str,
    payload_digest: str,
    payload_schema: int,
    idempotency_key: str,
    available_at: datetime,
) -> dict[str, Any]:
    if (
        not tenant_id
        or not IDENTIFIER.fullmatch(owner_ref)
        or not IDENTIFIER.fullmatch(job_type)
        or not DIGEST.fullmatch(payload_digest)
        or payload_schema < 1
        or not IDENTIFIER.fullmatch(idempotency_key)
        or available_at.tzinfo is None
    ):
        raise RuntimeRepositoryError('job:input_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                (f'{tenant_id}:{idempotency_key}',),
            )
            cursor.execute(
                """SELECT id,owner_ref,job_type,payload_digest,payload_schema,state
                   FROM sitecontent_durablejob WHERE site_id=%s AND idempotency_key=%s FOR UPDATE""",
                (tenant_id, idempotency_key),
            )
            prior = cursor.fetchone()
            if prior:
                if tuple(prior[1:5]) != (owner_ref, job_type, payload_digest, payload_schema):
                    raise RuntimeRepositoryError('job:idempotency_conflict')
                return {'jobId': str(prior[0]), 'state': prior[5], 'replayed': True}
            cursor.execute(
                """INSERT INTO sitecontent_durablejob
                   (id,site_id,owner_ref,generation,job_type,payload_digest,payload_schema,
                    idempotency_key,state,attempts,maximum_attempts,available_at,lease_owner,
                    result_digest,error_code,created_at,updated_at)
                   VALUES (gen_random_uuid(),%s,%s,1,%s,%s,%s,%s,'queued',0,5,%s,'','','',NOW(),NOW())
                   RETURNING id""",
                (
                    tenant_id,
                    owner_ref,
                    job_type,
                    payload_digest,
                    payload_schema,
                    idempotency_key,
                    available_at,
                ),
            )
            job_id = cursor.fetchone()[0]
        conn.commit()
    return {'jobId': str(job_id), 'state': 'queued', 'replayed': False}


def claim_jobs(
    *, tenant_id: str, worker: str, now: datetime, limit: int = 10
) -> list[dict[str, Any]]:
    if not worker or now.tzinfo is None or not 1 <= limit <= 25:
        raise RuntimeRepositoryError('job:limit_invalid')
    lease_token = uuid4()
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE sitecontent_durablejob
                   SET state='dead_letter',lease_owner='',lease_token=NULL,
                       lease_expires_at=NULL,error_code='job.attempts_exhausted',updated_at=NOW()
                   WHERE site_id=%s AND attempts>=maximum_attempts
                     AND (state IN ('queued','retry') OR
                          (state='leased' AND lease_expires_at<=%s))""",
                (tenant_id, now),
            )
            cursor.execute(
                """WITH candidates AS (
                       SELECT id FROM sitecontent_durablejob
                       WHERE site_id=%s AND available_at<=%s
                         AND (state IN ('queued','retry') OR (state='leased' AND lease_expires_at<=%s))
                         AND attempts<maximum_attempts
                       ORDER BY available_at,created_at,id FOR UPDATE SKIP LOCKED LIMIT %s
                   )
                   UPDATE sitecontent_durablejob AS job
                   SET state='leased',lease_owner=%s,lease_token=%s,lease_expires_at=%s,
                       attempts=attempts+1,updated_at=NOW()
                   FROM candidates WHERE job.id=candidates.id
                   RETURNING job.id,job.job_type,job.payload_digest,job.payload_schema,
                     job.attempts,job.generation,job.lease_token""",
                (tenant_id, now, now, limit, worker, str(lease_token), now + timedelta(minutes=15)),
            )
            rows = cursor.fetchall()
        conn.commit()
    return [
        {
            'jobId': str(row[0]),
            'jobType': row[1],
            'payloadDigest': row[2],
            'payloadSchema': row[3],
            'attempts': row[4],
            'generation': row[5],
            'leaseToken': str(row[6]),
        }
        for row in rows
    ]


def renew_job_lease(
    *,
    tenant_id: str,
    job_id: UUID,
    worker: str,
    lease_token: UUID,
    generation: int,
    now: datetime,
) -> None:
    """Validate a delivered claim immediately before work and renew its bound lease."""
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE sitecontent_durablejob
                   SET lease_expires_at=%s,updated_at=NOW()
                   WHERE site_id=%s AND id=%s AND state='leased' AND lease_owner=%s
                     AND lease_token=%s AND generation=%s AND lease_expires_at>%s""",
                (
                    now + timedelta(minutes=15),
                    tenant_id,
                    str(job_id),
                    worker,
                    str(lease_token),
                    generation,
                    now,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeRepositoryError('job:lease_lost')
        conn.commit()


def settle_job(
    *,
    tenant_id: str,
    job_id: UUID,
    worker: str,
    lease_token: UUID,
    generation: int,
    outcome: str,
    now: datetime,
    result_digest: str = '',
    error_code: str = '',
) -> str:
    if outcome not in {'succeeded', 'retry', 'dead_letter'}:
        raise RuntimeRepositoryError('job:outcome_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE sitecontent_durablejob SET
                          state=CASE WHEN %s='retry' AND attempts>=maximum_attempts
                                     THEN 'dead_letter' ELSE %s END,
                          lease_owner='',lease_token=NULL,lease_expires_at=NULL,
                          result_digest=%s,error_code=%s,
                          available_at=CASE WHEN %s='retry' THEN %s + LEAST(INTERVAL '1 hour',
                            make_interval(secs => (5 * power(2,attempts))::int)) ELSE available_at END,
                          updated_at=NOW()
                   WHERE site_id=%s AND id=%s AND state='leased' AND lease_owner=%s
                     AND lease_token=%s AND generation=%s AND lease_expires_at>%s
                   RETURNING state""",
                (
                    outcome,
                    outcome,
                    result_digest,
                    error_code,
                    outcome,
                    now,
                    tenant_id,
                    str(job_id),
                    worker,
                    str(lease_token),
                    generation,
                    now,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeRepositoryError('job:lease_lost')
        conn.commit()
    return str(row[0])


def dead_letters(*, tenant_id: str, limit: int = 25) -> list[dict[str, Any]]:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """SELECT id,job_type,error_code,attempts,updated_at FROM sitecontent_durablejob
               WHERE site_id=%s AND state='dead_letter' ORDER BY updated_at DESC,id LIMIT %s""",
            (tenant_id, min(max(limit, 1), 25)),
        )
        rows = cursor.fetchall()
    return [
        {
            'jobId': str(r[0]),
            'jobType': r[1],
            'errorCode': r[2],
            'attempts': r[3],
            'updatedAt': r[4].isoformat(),
        }
        for r in rows
    ]


def dead_letter_action(*, tenant_id: str, job_id: UUID, action: str, now: datetime) -> str:
    targets = {'replay': 'queued', 'cancel': 'cancelled'}
    if action not in targets:
        raise RuntimeRepositoryError('job:dead_letter_action_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE sitecontent_durablejob SET state=%s,generation=generation+1,
                          attempts=CASE WHEN %s='replay' THEN 0 ELSE attempts END,
                          available_at=%s,error_code='',updated_at=NOW()
                   WHERE site_id=%s AND id=%s AND state='dead_letter'""",
                (targets[action], action, now, tenant_id, str(job_id)),
            )
            if cursor.rowcount != 1:
                raise RuntimeRepositoryError('job:dead_letter_state_invalid')
        conn.commit()
    return targets[action]


def claim_due_schedules(*, tenant_id: str, now: datetime, limit: int = 25) -> list[dict[str, Any]]:
    if now.tzinfo is None:
        raise RuntimeRepositoryError('schedule:time_invalid')
    claim_token = uuid4()
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT id,schedule_key,job_type,timezone,rule,missed_policy,overlap_policy,
                          next_run_at,last_run_at,revision
                   FROM sitecontent_durableschedule
                   WHERE site_id=%s AND enabled AND next_run_at<=%s
                     AND (claim_token IS NULL OR claim_expires_at<=%s)
                     AND (SELECT COUNT(*) FROM sitecontent_durablejob
                          WHERE site_id=%s AND state IN ('queued','retry','leased')) < 100
                     AND NOT EXISTS (
                         SELECT 1 FROM sitecontent_durablejob AS active
                         WHERE active.site_id=%s
                           AND active.owner_ref='schedule:' || sitecontent_durableschedule.id::text
                           AND active.state='leased'
                     )
                     AND (
                         overlap_policy='replace' OR NOT EXISTS (
                             SELECT 1 FROM sitecontent_durablejob AS active
                             WHERE active.site_id=%s
                               AND active.owner_ref='schedule:' || sitecontent_durableschedule.id::text
                               AND active.state IN ('queued','retry','leased')
                         )
                     )
                   ORDER BY next_run_at,id FOR UPDATE SKIP LOCKED LIMIT %s""",
                (tenant_id, now, now, tenant_id, tenant_id, tenant_id, min(max(limit, 1), 25)),
            )
            rows = cursor.fetchall()
            claimed = []
            for row in rows:
                rule = str(row[4])
                try:
                    ZoneInfo(str(row[3]))
                except ZoneInfoNotFoundError as exc:
                    raise RuntimeRepositoryError('schedule:timezone_invalid') from exc
                if (
                    not rule.startswith('every:')
                    or not rule[6:].isdigit()
                    or row[5] not in {'skip', 'once'}
                    or row[6] not in {'forbid', 'replace'}
                ):
                    raise RuntimeRepositoryError('schedule:rule_invalid')
                seconds = int(rule[6:])
                if not 30 <= seconds <= 604800:
                    raise RuntimeRepositoryError('schedule:rule_invalid')
                original_due = row[7]
                if row[5] == 'once':
                    next_due = now + timedelta(seconds=seconds)
                else:
                    next_due = original_due + timedelta(seconds=seconds)
                    while next_due <= now:
                        next_due += timedelta(seconds=seconds)
                if row[6] == 'replace':
                    cursor.execute(
                        """UPDATE sitecontent_durablejob
                           SET state='cancelled',error_code='job.replaced_by_schedule',updated_at=NOW()
                           WHERE site_id=%s AND owner_ref=%s AND state IN ('queued','retry')""",
                        (tenant_id, f'schedule:{row[0]}'),
                    )
                cursor.execute(
                    """UPDATE sitecontent_durableschedule
                       SET last_run_at=next_run_at,next_run_at=%s,revision=revision+1,
                           claim_token=%s,claim_expires_at=%s,updated_at=NOW()
                       WHERE site_id=%s AND id=%s AND revision=%s""",
                    (
                        next_due,
                        str(claim_token),
                        now + timedelta(seconds=60),
                        tenant_id,
                        str(row[0]),
                        row[9],
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeRepositoryError('schedule:claim_lost')
                claimed.append(
                    {
                        'scheduleId': str(row[0]),
                        'scheduleKey': row[1],
                        'jobType': row[2],
                        'timezone': row[3],
                        'rule': row[4],
                        'missedPolicy': row[5],
                        'overlapPolicy': row[6],
                        'scheduledFor': original_due.isoformat(),
                        'nextRunAt': next_due.isoformat(),
                        'lastRunAt': original_due.isoformat(),
                        'revision': row[9] + 1,
                        'claimToken': str(claim_token),
                    }
                )
        conn.commit()
    return claimed


def due_schedules(*, tenant_id: str, now: datetime, limit: int = 25) -> list[dict[str, Any]]:
    """Compatibility entry point; due schedules are atomically claimed and advanced."""
    return claim_due_schedules(tenant_id=tenant_id, now=now, limit=limit)


def settle_schedule_claim(
    *,
    tenant_id: str,
    schedule_id: UUID,
    claim_token: UUID,
    revision: int,
    succeeded: bool,
    original_next_run_at: datetime,
) -> None:
    """Release a claim, restoring its due time when job materialization failed."""
    if revision < 1 or original_next_run_at.tzinfo is None:
        raise RuntimeRepositoryError('schedule:claim_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE sitecontent_durableschedule
                   SET next_run_at=CASE WHEN %s THEN next_run_at ELSE %s END,
                       claim_token=NULL,claim_expires_at=NULL,updated_at=NOW()
                   WHERE site_id=%s AND id=%s AND claim_token=%s AND revision=%s""",
                (
                    succeeded,
                    original_next_run_at,
                    tenant_id,
                    str(schedule_id),
                    str(claim_token),
                    revision,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeRepositoryError('schedule:claim_lost')
        conn.commit()
