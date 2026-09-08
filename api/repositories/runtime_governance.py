"""Tenant-scoped durable job, dead-letter, and scheduler repository."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from api.db import workspace_db_conn


class RuntimeRepositoryError(ValueError):
    pass


def enqueue_job(
    *, tenant_id: str, owner_ref: str, job_type: str, payload_digest: str,
    payload_schema: int, idempotency_key: str, available_at: datetime,
) -> dict[str, Any]:
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"{tenant_id}:{idempotency_key}",))
            cursor.execute(
                """SELECT id,owner_ref,job_type,payload_digest,payload_schema,state
                   FROM sitecontent_durablejob WHERE site_id=%s AND idempotency_key=%s FOR UPDATE""",
                (tenant_id, idempotency_key),
            )
            prior = cursor.fetchone()
            if prior:
                if tuple(prior[1:5]) != (owner_ref, job_type, payload_digest, payload_schema):
                    raise RuntimeRepositoryError("job:idempotency_conflict")
                return {"jobId": str(prior[0]), "state": prior[5], "replayed": True}
            cursor.execute(
                """INSERT INTO sitecontent_durablejob
                   (id,site_id,owner_ref,generation,job_type,payload_digest,payload_schema,
                    idempotency_key,state,attempts,maximum_attempts,available_at,lease_owner,
                    result_digest,error_code,created_at,updated_at)
                   VALUES (gen_random_uuid(),%s,%s,1,%s,%s,%s,%s,'queued',0,5,%s,'','','',NOW(),NOW())
                   RETURNING id""",
                (tenant_id, owner_ref, job_type, payload_digest, payload_schema, idempotency_key, available_at),
            )
            job_id = cursor.fetchone()[0]
        conn.commit()
    return {"jobId": str(job_id), "state": "queued", "replayed": False}


def claim_jobs(*, tenant_id: str, worker: str, now: datetime, limit: int = 10) -> list[dict[str, Any]]:
    if not 1 <= limit <= 25:
        raise RuntimeRepositoryError("job:limit_invalid")
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """WITH candidates AS (
                       SELECT id FROM sitecontent_durablejob
                       WHERE site_id=%s AND available_at<=%s
                         AND (state IN ('queued','retry') OR (state='leased' AND lease_expires_at<=%s))
                         AND attempts<maximum_attempts
                       ORDER BY available_at,created_at,id FOR UPDATE SKIP LOCKED LIMIT %s
                   )
                   UPDATE sitecontent_durablejob AS job
                   SET state='leased',lease_owner=%s,lease_expires_at=%s,attempts=attempts+1,updated_at=NOW()
                   FROM candidates WHERE job.id=candidates.id
                   RETURNING job.id,job.job_type,job.payload_digest,job.payload_schema,job.attempts""",
                (tenant_id, now, now, limit, worker, now + timedelta(seconds=60)),
            )
            rows = cursor.fetchall()
        conn.commit()
    return [
        {"jobId": str(row[0]), "jobType": row[1], "payloadDigest": row[2], "payloadSchema": row[3], "attempts": row[4]}
        for row in rows
    ]


def settle_job(
    *, tenant_id: str, job_id: UUID, worker: str, outcome: str,
    now: datetime, result_digest: str = "", error_code: str = "",
) -> str:
    if outcome not in {"succeeded", "retry", "dead_letter"}:
        raise RuntimeRepositoryError("job:outcome_invalid")
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE sitecontent_durablejob SET state=%s,lease_owner='',lease_expires_at=NULL,
                          result_digest=%s,error_code=%s,
                          available_at=CASE WHEN %s='retry' THEN %s + LEAST(INTERVAL '1 hour',
                            make_interval(secs => (5 * power(2,attempts))::int)) ELSE available_at END,
                          updated_at=NOW()
                   WHERE site_id=%s AND id=%s AND state='leased' AND lease_owner=%s""",
                (outcome, result_digest, error_code, outcome, now, tenant_id, str(job_id), worker),
            )
            if cursor.rowcount != 1:
                raise RuntimeRepositoryError("job:lease_lost")
        conn.commit()
    return outcome


def dead_letters(*, tenant_id: str, limit: int = 25) -> list[dict[str, Any]]:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """SELECT id,job_type,error_code,attempts,updated_at FROM sitecontent_durablejob
               WHERE site_id=%s AND state='dead_letter' ORDER BY updated_at DESC,id LIMIT %s""",
            (tenant_id, min(max(limit, 1), 25)),
        )
        rows = cursor.fetchall()
    return [{"jobId": str(r[0]), "jobType": r[1], "errorCode": r[2], "attempts": r[3], "updatedAt": r[4].isoformat()} for r in rows]


def dead_letter_action(*, tenant_id: str, job_id: UUID, action: str, now: datetime) -> str:
    targets = {"replay": "queued", "cancel": "cancelled"}
    if action not in targets:
        raise RuntimeRepositoryError("job:dead_letter_action_invalid")
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
                raise RuntimeRepositoryError("job:dead_letter_state_invalid")
        conn.commit()
    return targets[action]


def due_schedules(*, tenant_id: str, now: datetime, limit: int = 25) -> list[dict[str, Any]]:
    with workspace_db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cursor:
        cursor.execute(
            """SELECT id,schedule_key,job_type,timezone,rule,missed_policy,overlap_policy,
                      next_run_at,last_run_at,revision
               FROM sitecontent_durableschedule WHERE site_id=%s AND enabled AND next_run_at<=%s
               ORDER BY next_run_at,id LIMIT %s""",
            (tenant_id, now, min(max(limit, 1), 25)),
        )
        rows = cursor.fetchall()
    return [
        {"scheduleId": str(r[0]), "scheduleKey": r[1], "jobType": r[2], "timezone": r[3],
         "rule": r[4], "missedPolicy": r[5], "overlapPolicy": r[6],
         "nextRunAt": r[7].isoformat(), "lastRunAt": r[8].isoformat() if r[8] else None,
         "revision": r[9]}
        for r in rows
    ]
