"""Bounded review-only LOCAL TEST adapter. This module never sends email.

The durable effect is a receipt in the same PostgreSQL transaction as the intent.
Transaction-scoped locks are the claim/fence: there is no external-call gap, lease,
provider, configurable adapter, or in-memory deduplication cache. Process death rolls
back both claim and effect; a lost commit response is safe to replay. The caller must
supply the deployment's trusted manifest site, never request-selected scope.

A digest batch's 'closed' state means frozen membership, NOT pending or delivered.
If every member is suppressed it remains closed with no receipt/delivered_at; the
terminal member statuses establish no delivery and exclude it from future work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4

from api.db import workspace_worker_db_conn as db_conn
from api.repositories import workspace_policy as policy_repository
from api.security.tenant_context import canonical_tenant_id

ADAPTER = 'local_test'
MAX_ATTEMPTS = 8
MAX_BATCH_ITEMS = 100
INTENT_COLUMNS = 'id,record_id,submission_id,subject_revision,recipient_id,attempts'


@dataclass(frozen=True)
class Intent:
    id: UUID
    record_id: UUID
    submission_id: UUID
    subject_revision: UUID
    recipient_id: UUID
    attempts: int


def _decision(cur, *, site_id: str, item: Intent, policy: dict) -> str:
    # Caller holds the feature/policy lock before locking content, subject, identity.
    cur.execute(
        """SELECT c.state,c.deleted_at,s.schema_version,s.semantic_revision,
        s.submission_id,s.original_creator_id,s.semantic_author_id,s.submitter_id,
        s.adopted_snapshot,s.fingerprint
        FROM sitecontent_contentrecord c JOIN sitecontent_reviewsubject s
          ON s.record_id=c.id AND s.site_id=c.site_id
        WHERE c.site_id=%s AND c.id=%s FOR UPDATE OF c,s""",
        (site_id, str(item.record_id)),
    )
    row = cur.fetchone()
    if not row:
        return 'ineligible'
    (
        state,
        deleted,
        schema,
        revision,
        submission,
        creator,
        author,
        submitter,
        adopted,
        fingerprint,
    ) = row
    # Optional workflow requests notify another publisher, not necessarily an
    # independent author. Required review retains all canonical author exclusions.
    # Always re-evaluate the current policy; never expand an existing intent audience.
    subject = dict(
        original_creator_id=creator,
        semantic_author_id=author,
        submitter_id=submitter,
        adopted_snapshot=adopted,
    )
    if (
        state != 'in_review'
        or deleted is not None
        or schema != 1
        or str(revision) != str(item.subject_revision)
        or str(submission) != str(item.submission_id)
        or not submitter
        or str(submitter) == str(item.recipient_id)
        or (
            policy['require_review']
            and not policy_repository.review_is_independent(subject, str(item.recipient_id))
        )
    ):
        return 'ineligible'
    if (
        policy_repository.current_fingerprint(cur, site_id=site_id, record_id=item.record_id)
        != fingerprint
    ):
        return 'ineligible'
    try:
        membership = policy_repository.member(
            cur,
            site_id=site_id,
            user_id=item.recipient_id,
            permission='review' if policy['require_review'] else 'publish',
            lock=True,
        )
    except PermissionError:
        return 'ineligible'
    if policy.get('organization_id') and policy['organization_id'] != membership['organization_id']:
        return 'ineligible'
    cur.execute('SELECT base2_workspace_product_delivery(%s,%s)', (site_id, str(item.recipient_id)))
    preference = cur.fetchone()
    return (
        preference[0]
        if preference and preference[0] in {'immediate', 'digest', 'disabled'}
        else 'ineligible'
    )


def _receipt(cur, *, site_id, recipient_id, now, intent_id=None, batch_id=None):
    if (intent_id is None) == (batch_id is None):
        raise ValueError('review_delivery_source_invalid')
    source = f'intent:{site_id}:{intent_id}' if intent_id else f'digest:{site_id}:{batch_id}'
    cur.execute(
        """INSERT INTO sitecontent_reviewnotificationdelivery
        (id,site_id,recipient_id,effect_key,intent_id,digest_batch_id,delivered_at,created_at,updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (effect_key) DO NOTHING""",
        (
            str(uuid4()),
            site_id,
            str(recipient_id),
            f'review:{source}',
            str(intent_id) if intent_id else None,
            str(batch_id) if batch_id else None,
            now,
            now,
            now,
        ),
    )


def _finish(cur, *, site_id, item, status, now, reason=''):
    cur.execute(
        """UPDATE sitecontent_reviewnotificationintent SET status=%s,
        delivered_at=%s,last_error_code=%s,updated_at=%s
        WHERE site_id=%s AND id=%s AND status IN ('pending','digest')""",
        (status, now if status == 'delivered' else None, reason, now, site_id, str(item.id)),
    )


def _retry(cur, *, site_id, items, now):
    outcomes = {'failed': 0, 'retry': 0}
    for item in items:
        status = 'failed' if item.attempts + 1 >= MAX_ATTEMPTS else 'pending'
        # Preserve digest assignment; callers use that immutable FK for batch retries.
        outcomes['failed' if status == 'failed' else 'retry'] += 1
        cur.execute(
            """UPDATE sitecontent_reviewnotificationintent
            SET attempts=attempts+1,status=CASE WHEN %s='failed' THEN 'failed'
                WHEN digest_batch_id IS NOT NULL THEN 'digest' ELSE 'pending' END,
                available_at=%s,last_error_code=%s,updated_at=%s
            WHERE site_id=%s AND id=%s AND status IN ('pending','digest') AND attempts<8""",
            (
                status,
                now + timedelta(seconds=min(60 * 2**item.attempts, 3600)),
                'review_delivery_unavailable',
                now,
                site_id,
                str(item.id),
            ),
        )
    return outcomes


def _assign_digest(cur, *, site_id, item, now):
    date = now.date() + timedelta(days=1)
    # Bounded daily batches. A closed/full day's membership never grows. Late arrivals
    # move to a later UTC day rather than conflict-ignore into a dropped notification.
    for _ in range(32):
        cur.execute(
            """SELECT b.id,b.status,(SELECT count(*) FROM sitecontent_reviewnotificationintent i
            WHERE i.site_id=b.site_id AND i.digest_batch_id=b.id)
            FROM sitecontent_reviewdigestbatch b
            WHERE b.site_id=%s AND b.recipient_id=%s AND b.digest_date=%s FOR UPDATE OF b""",
            (site_id, str(item.recipient_id), date),
        )
        batch = cur.fetchone()
        if batch is None:
            batch_id = str(uuid4())
            cur.execute(
                """INSERT INTO sitecontent_reviewdigestbatch
                (id,site_id,recipient_id,digest_date,status,created_at,updated_at)
                VALUES (%s,%s,%s,%s,'open',%s,%s)""",
                (batch_id, site_id, str(item.recipient_id), date, now, now),
            )
            break
        if batch[1] == 'open' and batch[2] < MAX_BATCH_ITEMS:
            batch_id = str(batch[0])
            break
        date += timedelta(days=1)
    else:
        raise RuntimeError('review_digest_capacity_unavailable')
    boundary = datetime.combine(date, time.min, tzinfo=UTC)
    cur.execute(
        """UPDATE sitecontent_reviewnotificationintent SET status='digest',
        digest_batch_id=%s,available_at=%s,last_error_code='',updated_at=%s
        WHERE site_id=%s AND id=%s AND status='pending' AND digest_batch_id IS NULL""",
        (batch_id, boundary, now, site_id, str(item.id)),
    )


def _process_pending(cur, *, site_id, item, policy, now):
    mode = _decision(cur, site_id=site_id, item=item, policy=policy)
    if mode == 'immediate':
        _receipt(cur, site_id=site_id, recipient_id=item.recipient_id, intent_id=item.id, now=now)
        _finish(cur, site_id=site_id, item=item, status='delivered', now=now)
        return 'delivered'
    if mode == 'digest':
        _assign_digest(cur, site_id=site_id, item=item, now=now)
        return 'digest'
    _finish(
        cur,
        site_id=site_id,
        item=item,
        status='suppressed',
        now=now,
        reason='review_opted_out' if mode == 'disabled' else 'review_ineligible',
    )
    return 'suppressed'


def _process_batch(cur, *, site_id, batch_id, recipient_id, items, policy, now):
    eligible = []
    suppressed = 0
    for item in items:
        if _decision(cur, site_id=site_id, item=item, policy=policy) == 'digest':
            eligible.append(item)
        else:
            # A changed immediate preference must not be relabelled as digest.
            _finish(
                cur,
                site_id=site_id,
                item=item,
                status='suppressed',
                now=now,
                reason='review_digest_ineligible',
            )
            suppressed += 1
    if eligible:
        _receipt(cur, site_id=site_id, recipient_id=recipient_id, batch_id=batch_id, now=now)
        for item in eligible:
            _finish(cur, site_id=site_id, item=item, status='delivered', now=now)
    cur.execute(
        """UPDATE sitecontent_reviewdigestbatch SET status=%s,
        delivered_at=%s,updated_at=%s WHERE site_id=%s AND id=%s AND status='closed' """,
        (
            'delivered' if eligible else 'closed',
            now if eligible else None,
            now,
            site_id,
            str(batch_id),
        ),
    )
    return len(eligible), suppressed


def process_review_notifications(
    *, site_id: str, now: datetime | None = None, limit: int = 25
) -> dict:
    """Process a bounded pass; 'delivered' means a LOCAL TEST database receipt only.

    Unknown adapter/environment values cannot activate delivery: there is no such
    configuration path. No credentials, transport, recipient address or arbitrary
    recipient input is accepted. Dependency errors never masquerade as opt-out.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError('review_notification_limit_invalid')
    if canonical_tenant_id(site_id) != site_id:
        raise ValueError('review_notification_scope_invalid')
    now = now or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('review_notification_clock_invalid')
    now = now.astimezone(UTC)
    counts = dict(delivered=0, digest=0, suppressed=0, retry=0, failed=0)
    with db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                policy_repository.begin_effect(cur)
                policy = policy_repository.read_policy(cur, site_id=site_id, lock=True)
                cur.execute(
                    f"""SELECT {INTENT_COLUMNS} FROM sitecontent_reviewnotificationintent
                    WHERE site_id=%s AND status='pending' AND digest_batch_id IS NULL
                      AND attempts<8 AND available_at<=%s
                    ORDER BY available_at,id LIMIT %s FOR UPDATE SKIP LOCKED""",
                    (site_id, now, limit),
                )
                pending = [Intent(*row) for row in cur.fetchall()]
                for item in pending:
                    cur.execute('SAVEPOINT review_delivery')
                    try:
                        outcome = _process_pending(
                            cur, site_id=site_id, item=item, policy=policy, now=now
                        )
                    except Exception:
                        cur.execute('ROLLBACK TO SAVEPOINT review_delivery')
                        outcomes = _retry(cur, site_id=site_id, items=[item], now=now)
                        counts['failed'] += outcomes['failed']
                        counts['retry'] += outcomes['retry']
                    else:
                        counts[outcome] += 1
                    cur.execute('RELEASE SAVEPOINT review_delivery')
                cur.execute(
                    """SELECT b.id,b.recipient_id FROM sitecontent_reviewdigestbatch b
                    WHERE b.site_id=%s AND b.status IN ('open','closed') AND b.digest_date<=%s
                    AND EXISTS (SELECT 1 FROM sitecontent_reviewnotificationintent i
                        WHERE i.site_id=b.site_id AND i.digest_batch_id=b.id AND i.status='digest')
                    AND NOT EXISTS (SELECT 1 FROM sitecontent_reviewnotificationintent i
                        WHERE i.site_id=b.site_id AND i.digest_batch_id=b.id
                          AND i.status='digest' AND i.available_at>%s)
                    ORDER BY b.digest_date,b.id LIMIT %s FOR UPDATE OF b SKIP LOCKED""",
                    (site_id, now.date(), now, limit),
                )
                batches = cur.fetchall()
                for batch_id, recipient_id in batches:
                    cur.execute(
                        """UPDATE sitecontent_reviewdigestbatch SET status='closed',
                        closed_at=COALESCE(closed_at,%s),updated_at=%s WHERE site_id=%s AND id=%s""",
                        (now, now, site_id, str(batch_id)),
                    )
                    cur.execute(
                        f"""SELECT {INTENT_COLUMNS} FROM sitecontent_reviewnotificationintent
                        WHERE site_id=%s AND digest_batch_id=%s AND status='digest'
                        ORDER BY id LIMIT %s FOR UPDATE""",
                        (site_id, str(batch_id), MAX_BATCH_ITEMS + 1),
                    )
                    items = [Intent(*row) for row in cur.fetchall()]
                    if len(items) > MAX_BATCH_ITEMS:
                        raise RuntimeError('review_digest_membership_invalid')
                    cur.execute('SAVEPOINT review_delivery')
                    try:
                        delivered, suppressed = _process_batch(
                            cur,
                            site_id=site_id,
                            batch_id=batch_id,
                            recipient_id=recipient_id,
                            items=items,
                            policy=policy,
                            now=now,
                        )
                        counts['delivered'] += delivered
                        counts['suppressed'] += suppressed
                    except Exception:
                        cur.execute('ROLLBACK TO SAVEPOINT review_delivery')
                        outcomes = _retry(cur, site_id=site_id, items=items, now=now)
                        counts['failed'] += outcomes['failed']
                        counts['retry'] += outcomes['retry']
                        if outcomes['failed'] and not outcomes['retry']:
                            cur.execute(
                                "UPDATE sitecontent_reviewdigestbatch SET status='failed',updated_at=%s WHERE site_id=%s AND id=%s",
                                (now, site_id, str(batch_id)),
                            )
                    cur.execute('RELEASE SAVEPOINT review_delivery')
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {'adapter': ADAPTER, **counts}
