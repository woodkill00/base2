"""Tenant-scoped durable job, dead-letter, and scheduler repository."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api.db import workspace_db_conn


class RuntimeRepositoryError(ValueError):
    pass


IDENTIFIER = re.compile(r'^[a-z][a-z0-9_.:-]{2,127}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')
SCHEDULE_ISO_KEY = re.compile(
    r'^schedule:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:'
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$'
)
DAILY_RULE = re.compile(r'^daily:(\d{2}):(\d{2})$')


def _stored_idempotency_key(value: str) -> str:
    """Map the one supported ISO-derived schedule key into the DB-safe alphabet."""
    if IDENTIFIER.fullmatch(value or ''):
        return value
    if not SCHEDULE_ISO_KEY.fullmatch(value or ''):
        raise RuntimeRepositoryError('job:input_invalid')
    timestamp_text = value.split(':', 2)[2]
    try:
        timestamp = datetime.fromisoformat(timestamp_text.replace('Z', '+00:00'))
    except ValueError as exc:
        raise RuntimeRepositoryError('job:input_invalid') from exc
    if timestamp.tzinfo is None:
        raise RuntimeRepositoryError('job:input_invalid')
    return f'schedule-iso:{hashlib.sha256(value.encode()).hexdigest()}'


def _retry_delay_seconds(*, job_id: UUID, generation: int, attempts: int) -> int:
    """Return deterministic, bounded exponential backoff with up to 20% jitter."""
    if generation < 1 or attempts < 1:
        raise RuntimeRepositoryError('job:retry_state_invalid')
    base = min(3600, 5 * (2**attempts))
    if base >= 3600:
        return 3600
    ceiling = max(1, base // 5)
    seed = hashlib.sha256(f'{job_id}:{generation}:{attempts}'.encode()).digest()
    return min(3600, base + int.from_bytes(seed[:4], 'big') % (ceiling + 1))


def _next_daily_run(*, reference: datetime, zone: ZoneInfo, hour: int, minute: int) -> datetime:
    """Choose the first valid wall time after reference; gaps skip and folds run once."""
    local_reference = reference.astimezone(zone)
    for offset in range(0, 370):
        day = local_reference.date() + timedelta(days=offset)
        wall = datetime.combine(day, time(hour=hour, minute=minute))
        # fold=0 deliberately selects the first occurrence on a fall-back day.
        candidate = wall.replace(tzinfo=zone, fold=0)
        round_trip = candidate.astimezone(UTC).astimezone(zone)
        if round_trip.replace(tzinfo=None) != wall or round_trip.fold != 0:
            # A spring-forward gap is not a real instant, so safely skip it.
            continue
        if candidate > reference:
            return candidate
    raise RuntimeRepositoryError('schedule:next_run_unavailable')


def _next_schedule_run(
    *, rule: str, zone: ZoneInfo, due: datetime, now: datetime, missed: str
) -> datetime:
    if rule.startswith('every:') and rule[6:].isdigit():
        seconds = int(rule[6:])
        if not 30 <= seconds <= 604800:
            raise RuntimeRepositoryError('schedule:rule_invalid')
        if missed == 'once':
            return now + timedelta(seconds=seconds)
        candidate = due + timedelta(seconds=seconds)
        while candidate <= now:
            candidate += timedelta(seconds=seconds)
        return candidate
    match = DAILY_RULE.fullmatch(rule)
    if match:
        hour, minute = (int(value) for value in match.groups())
        if hour > 23 or minute > 59:
            raise RuntimeRepositoryError('schedule:rule_invalid')
        return _next_daily_run(reference=now, zone=zone, hour=hour, minute=minute)
    raise RuntimeRepositoryError('schedule:rule_invalid')


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
    stored_idempotency_key = _stored_idempotency_key(idempotency_key)
    if (
        not tenant_id
        or not IDENTIFIER.fullmatch(owner_ref)
        or not IDENTIFIER.fullmatch(job_type)
        or not DIGEST.fullmatch(payload_digest)
        or payload_schema < 1
        or available_at.tzinfo is None
    ):
        raise RuntimeRepositoryError('job:input_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                (f'{tenant_id}:{stored_idempotency_key}',),
            )
            cursor.execute(
                """SELECT id,owner_ref,job_type,payload_digest,payload_schema,state
                   FROM sitecontent_durablejob WHERE site_id=%s AND idempotency_key=%s FOR UPDATE""",
                (tenant_id, stored_idempotency_key),
            )
            prior = cursor.fetchone()
            if prior:
                if tuple(prior[1:5]) != (owner_ref, job_type, payload_digest, payload_schema):
                    raise RuntimeRepositoryError('job:idempotency_conflict')
                return {'jobId': str(prior[0]), 'state': prior[5], 'replayed': True}
            cursor.execute(
                'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                (f'{tenant_id}:schedule-capacity',),
            )
            schedule_id = (
                owner_ref.removeprefix('schedule:') if owner_ref.startswith('schedule:') else ''
            )
            cursor.execute(
                """SELECT
                     (SELECT COUNT(*) FROM sitecontent_durablejob
                      WHERE site_id=%s AND state IN ('queued','retry','leased'))
                     +(SELECT COUNT(*) FROM sitecontent_durableschedule AS reserved
                       WHERE reserved.site_id=%s AND reserved.claim_token IS NOT NULL
                         AND reserved.claim_expires_at>NOW()
                         AND NOT EXISTS (
                           SELECT 1 FROM sitecontent_durablejob AS materialized
                           WHERE materialized.site_id=reserved.site_id
                             AND materialized.owner_ref='schedule:' || reserved.id::text
                             AND materialized.state IN ('queued','retry','leased'))),
                     EXISTS(SELECT 1 FROM sitecontent_durableschedule
                            WHERE site_id=%s AND id::text=%s AND claim_token IS NOT NULL
                              AND claim_expires_at>NOW())""",
                (tenant_id, tenant_id, tenant_id, schedule_id),
            )
            used_capacity, has_reservation = cursor.fetchone()
            if int(used_capacity) >= 100 and not (has_reservation and int(used_capacity) == 100):
                raise RuntimeRepositoryError('job:capacity_exhausted')
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
                    stored_idempotency_key,
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
                          (state='leased' AND lease_expires_at<=NOW()))""",
                (tenant_id,),
            )
            cursor.execute(
                """WITH candidates AS (
                       SELECT id FROM sitecontent_durablejob
                       WHERE site_id=%s AND available_at<=%s
                         AND (state IN ('queued','retry') OR
                              (state='leased' AND lease_expires_at<=NOW()))
                         AND attempts<maximum_attempts
                       ORDER BY available_at,created_at,id FOR UPDATE SKIP LOCKED LIMIT %s
                   )
                   UPDATE sitecontent_durablejob AS job
                   SET state='leased',lease_owner=%s,lease_token=%s,
                       lease_expires_at=NOW()+INTERVAL '15 minutes',
                       attempts=attempts+1,updated_at=NOW()
                   FROM candidates WHERE job.id=candidates.id
                   RETURNING job.id,job.job_type,job.payload_digest,job.payload_schema,
                     job.attempts,job.generation,job.lease_token""",
                (tenant_id, now, limit, worker, str(lease_token)),
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
    if now.tzinfo is None:
        raise RuntimeRepositoryError('job:time_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE sitecontent_durablejob
                   SET lease_expires_at=NOW()+INTERVAL '15 minutes',updated_at=NOW()
                   WHERE site_id=%s AND id=%s AND state='leased' AND lease_owner=%s
                     AND lease_token=%s AND generation=%s AND lease_expires_at>NOW()""",
                (
                    tenant_id,
                    str(job_id),
                    worker,
                    str(lease_token),
                    generation,
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
    if outcome not in {'succeeded', 'retry', 'dead_letter'} or now.tzinfo is None:
        raise RuntimeRepositoryError('job:outcome_invalid')
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT attempts FROM sitecontent_durablejob
                   WHERE site_id=%s AND id=%s AND state='leased' AND lease_owner=%s
                     AND lease_token=%s AND generation=%s AND lease_expires_at>NOW()
                   FOR UPDATE""",
                (tenant_id, str(job_id), worker, str(lease_token), generation),
            )
            attempt_row = cursor.fetchone()
            if attempt_row is None:
                raise RuntimeRepositoryError('job:lease_lost')
            retry_delay = _retry_delay_seconds(
                job_id=job_id, generation=generation, attempts=int(attempt_row[0])
            )
            cursor.execute(
                """UPDATE sitecontent_durablejob SET
                          state=CASE WHEN %s='retry' AND attempts>=maximum_attempts
                                     THEN 'dead_letter' ELSE %s END,
                          lease_owner='',lease_token=NULL,lease_expires_at=NULL,
                          result_digest=%s,error_code=%s,
                          available_at=CASE WHEN %s='retry'
                            THEN NOW()+make_interval(secs => %s) ELSE available_at END,
                          updated_at=NOW()
                   WHERE site_id=%s AND id=%s AND state='leased' AND lease_owner=%s
                     AND lease_token=%s AND generation=%s AND lease_expires_at>NOW()
                   RETURNING state""",
                (
                    outcome,
                    outcome,
                    result_digest,
                    error_code,
                    outcome,
                    retry_delay,
                    tenant_id,
                    str(job_id),
                    worker,
                    str(lease_token),
                    generation,
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
            # Claims are capacity reservations. Count live jobs plus unexpired
            # schedule claims under one tenant-scoped transaction lock so
            # concurrent materializers cannot oversubscribe the fixed ceiling.
            cursor.execute(
                'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                (f'{tenant_id}:schedule-capacity',),
            )
            cursor.execute(
                """SELECT GREATEST(0,100
                     -(SELECT COUNT(*) FROM sitecontent_durablejob
                       WHERE site_id=%s AND state IN ('queued','retry','leased'))
                     -(SELECT COUNT(*) FROM sitecontent_durableschedule AS reserved
                       WHERE reserved.site_id=%s AND reserved.claim_token IS NOT NULL
                         AND reserved.claim_expires_at>NOW()
                         AND NOT EXISTS (
                           SELECT 1 FROM sitecontent_durablejob AS materialized
                           WHERE materialized.site_id=reserved.site_id
                             AND materialized.owner_ref='schedule:' || reserved.id::text
                             AND materialized.state IN ('queued','retry','leased'))))""",
                (tenant_id, tenant_id),
            )
            capacity = min(int(cursor.fetchone()[0]), min(max(limit, 1), 25))
            if capacity == 0:
                conn.commit()
                return []
            cursor.execute(
                """SELECT id,schedule_key,job_type,timezone,rule,missed_policy,overlap_policy,
                          next_run_at,last_run_at,revision
                   FROM sitecontent_durableschedule
                   WHERE site_id=%s AND enabled AND next_run_at<=%s
                     AND (claim_token IS NULL OR claim_expires_at<=%s)
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
                (tenant_id, now, now, tenant_id, tenant_id, capacity),
            )
            rows = cursor.fetchall()
            claimed = []
            for row in rows:
                rule = str(row[4])
                try:
                    zone = ZoneInfo(str(row[3]))
                except ZoneInfoNotFoundError as exc:
                    raise RuntimeRepositoryError('schedule:timezone_invalid') from exc
                if row[5] not in {'skip', 'once'} or row[6] not in {'forbid', 'replace'}:
                    raise RuntimeRepositoryError('schedule:rule_invalid')
                original_due = row[7]
                next_due = _next_schedule_run(
                    rule=rule, zone=zone, due=original_due, now=now, missed=str(row[5])
                )
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
