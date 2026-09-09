from __future__ import annotations

import logging
import os
import re
import stat as stat_module
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from api.db import db_conn
from api.services.transactional_email import (
    DisabledEmailAdapter,
    LocalFakeEmailAdapter,
    RenderedEmail,
    SmtpEmailAdapter,
    deliver_email,
    recipient_digest,
)


logger = logging.getLogger('api.email')


@dataclass(frozen=True)
class EmailOutboxRow:
    id: UUID
    to_email: str
    subject: str
    body_text: str
    body_html: str
    status: str
    provider: str
    provider_message_id: str
    error: str
    created_at: datetime
    sent_at: datetime | None
    claim_token: UUID | None = None
    delivery_key: str = ''


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_outbox_email(
    *, to_email: str, subject: str, body_text: str, body_html: str = ''
) -> EmailOutboxRow:
    outbox_id = uuid4()
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_email_outbox(
                    id, to_email, subject, body_text, body_html, delivery_key
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, to_email, subject, body_text, body_html, status, provider, provider_message_id, error, created_at, sent_at, claim_token, delivery_key
                """,
                (
                    str(outbox_id),
                    to_email,
                    subject,
                    body_text,
                    body_html or '',
                    str(outbox_id),
                ),
            )
            row = cur.fetchone()

    return EmailOutboxRow(
        id=UUID(str(row[0])),
        to_email=row[1],
        subject=row[2],
        body_text=row[3],
        body_html=row[4] or '',
        status=row[5],
        provider=row[6],
        provider_message_id=row[7] or '',
        error=row[8] or '',
        created_at=row[9],
        sent_at=row[10],
        claim_token=UUID(str(row[11])) if row[11] else None,
        delivery_key=row[12] or str(row[0]),
    )


def get_outbox_email(outbox_id: UUID) -> EmailOutboxRow | None:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, to_email, subject, body_text, body_html, status, provider, provider_message_id, error, created_at, sent_at, claim_token, delivery_key
            FROM api_email_outbox
            WHERE id=%s
            """,
            (str(outbox_id),),
        )
        row = cur.fetchone()

    if not row:
        return None

    return EmailOutboxRow(
        id=UUID(str(row[0])),
        to_email=row[1],
        subject=row[2],
        body_text=row[3],
        body_html=row[4] or '',
        status=row[5],
        provider=row[6],
        provider_message_id=row[7] or '',
        error=row[8] or '',
        created_at=row[9],
        sent_at=row[10],
        claim_token=UUID(str(row[11])) if row[11] else None,
        delivery_key=row[12] or str(row[0]),
    )


def claim_outbox_email(outbox_id: UUID) -> EmailOutboxRow | None:
    """Atomically lease a due row; abandoned leases become eligible after five minutes."""
    claim_token = uuid4()
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_email_outbox
                SET status='sending', provider='worker_claim', provider_message_id='',
                    claim_token=%s, claim_expires_at=NOW() + INTERVAL '5 minutes'
                WHERE id=%s AND (
                    status IN ('queued', 'retry') OR (
                        status='sending' AND claim_expires_at < NOW()
                    )
                )
                RETURNING id, to_email, subject, body_text, body_html, status, provider,
                          provider_message_id, error, created_at, sent_at, claim_token, delivery_key
                """,
                (str(claim_token), str(outbox_id)),
            )
            row = cur.fetchone()
    if not row:
        return None
    return EmailOutboxRow(
        id=UUID(str(row[0])),
        to_email=row[1],
        subject=row[2],
        body_text=row[3],
        body_html=row[4] or '',
        status=row[5],
        provider=row[6],
        provider_message_id=row[7] or '',
        error=row[8] or '',
        created_at=row[9],
        sent_at=row[10],
        claim_token=UUID(str(row[11])),
        delivery_key=row[12] or str(row[0]),
    )


def mark_outbox_status(
    *,
    outbox_id: UUID,
    claim_token: UUID,
    status: str,
    provider: str,
    provider_message_id: str = '',
    error: str = '',
) -> bool:
    if status not in {'queued', 'sent', 'disabled', 'suppressed', 'retry', 'dead_letter'}:
        raise ValueError('outbox_status_invalid')
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_email_outbox
                SET status=%s, provider=%s, provider_message_id=%s, error=%s,
                    sent_at=CASE WHEN %s='sent' THEN NOW() ELSE sent_at END,
                    claim_token=NULL, claim_expires_at=NULL
                WHERE id=%s AND status='sending' AND claim_token=%s
                """,
                (
                    status,
                    provider,
                    provider_message_id[:255],
                    error[:2000],
                    status,
                    str(outbox_id),
                    str(claim_token),
                ),
            )
            return cur.rowcount == 1


def safe_outbox_diagnostic(row: EmailOutboxRow) -> dict[str, object]:
    return {
        'id': str(row.id),
        'recipientDigest': recipient_digest(row.to_email),
        'status': row.status,
        'provider': row.provider,
        'createdAt': row.created_at.isoformat(),
        'sentAt': row.sent_at.isoformat() if row.sent_at else None,
        'hasError': bool(row.error),
    }


def _configured_adapter():
    mode = os.getenv('BASE2_EMAIL_ADAPTER', 'disabled').strip().lower()
    if mode == 'local_fake':
        return LocalFakeEmailAdapter()
    if mode == 'smtp':

        def private_value(variable: str) -> str:
            path = os.getenv(variable, '').strip()
            if not path or not os.path.isabs(path) or os.path.islink(path):
                raise RuntimeError('email_secret_file_invalid')
            stat = os.stat(path, follow_symlinks=False)
            if not stat_module.S_ISREG(stat.st_mode):
                raise RuntimeError('email_secret_file_invalid')
            if stat.st_uid != os.geteuid() or stat.st_mode & 0o077:
                raise RuntimeError('email_secret_file_permissions')
            with open(path, encoding='utf-8') as handle:
                value = handle.read().strip()
            if not value:
                raise RuntimeError('email_secret_empty')
            return value

        try:
            port = int(os.getenv('BASE2_EMAIL_SMTP_PORT', '587'))
            timeout = float(os.getenv('BASE2_EMAIL_SMTP_TIMEOUT_SECONDS', '10'))
        except ValueError as exc:
            raise RuntimeError('email_smtp_configuration_invalid') from exc
        return SmtpEmailAdapter(
            host=os.getenv('BASE2_EMAIL_SMTP_HOST', '').strip(),
            port=port,
            username=private_value('BASE2_EMAIL_SMTP_USERNAME_FILE'),
            password=private_value('BASE2_EMAIL_SMTP_PASSWORD_FILE'),
            from_address=os.getenv('BASE2_EMAIL_FROM_ADDRESS', '').strip(),
            timeout=timeout,
        )
    if mode != 'disabled':
        raise RuntimeError('email_adapter_not_allowed')
    return DisabledEmailAdapter()


def process_outbox_email(*, outbox_id: UUID) -> None:
    """Process an outbox row.

    The configured bounded adapter may use the local test backend or authenticated
    SMTP delivery. Disabled mode fails closed without marking the message sent.
    """

    existing = claim_outbox_email(outbox_id)
    if existing is None:
        current = get_outbox_email(outbox_id)
        if current is None:
            raise RuntimeError('outbox_not_found')
        # Another worker owns the lease or this row is already terminal.
        return
    if existing.claim_token is None:
        raise RuntimeError('outbox_claim_fence_missing')

    adapter = _configured_adapter()
    match = re.fullmatch(r'delivery_retry:(\d+)', existing.error or '')
    attempt = int(match.group(1)) + 1 if match else 1
    result = deliver_email(
        RenderedEmail(
            kind='outbox',
            recipient=existing.to_email,
            subject=existing.subject,
            text=existing.body_text,
            html=existing.body_html,
            delivery_key=existing.delivery_key or str(existing.id),
        ),
        adapter,
        attempt=attempt,
        max_attempts=3,
    )
    settled = mark_outbox_status(
        outbox_id=outbox_id,
        claim_token=existing.claim_token,
        status='retry' if result.status == 'disabled' else result.status,
        provider=result.provider,
        provider_message_id=result.message_id,
        error=(
            ''
            if result.status == 'sent'
            else f'delivery_retry:{attempt}'
            if result.status in {'retry', 'disabled'}
            else f'delivery_{result.status}'
        ),
    )
    if not settled:
        raise RuntimeError('outbox_claim_lost')


def replayable_outbox_ids(*, limit: int = 100) -> list[UUID]:
    if limit < 1 or limit > 500:
        raise ValueError('outbox_replay_limit_invalid')
    with db_conn() as conn:
        with conn.cursor() as cur:
            # SMTP acceptance and the terminal database write cannot be atomic.
            # Never silently resend an expired in-flight delivery; surface it
            # for explicit provider/manual reconciliation.
            cur.execute(
                """UPDATE api_email_outbox
                      SET status='failed', error='delivery_uncertain_manual_reconciliation',
                          claim_token=NULL, claim_expires_at=NULL
                    WHERE status='sending' AND claim_expires_at < NOW()
                      AND sent_at IS NULL"""
            )
            cur.execute(
                """SELECT id FROM api_email_outbox
                    WHERE status IN ('queued', 'retry') AND sent_at IS NULL
                    ORDER BY created_at ASC, id ASC LIMIT %s""",
                (limit,),
            )
            rows = cur.fetchall()
        conn.commit()
    return [UUID(str(row[0])) for row in rows]


def queue_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str = '',
    request_id: str | None = None,
    send_async: bool = True,
) -> EmailOutboxRow:
    outbox = create_outbox_email(
        to_email=to_email, subject=subject, body_text=body_text, body_html=body_html
    )

    if not send_async:
        return outbox

    try:
        # Import inside function so tests can run without Celery broker.
        from api.tasks import app as celery_app

        celery_app.send_task(
            'app.send_email_outbox',
            args=[str(outbox.id)],
            kwargs={'request_id': request_id},
        )
    except Exception as e:
        # Never fail the request path because the broker is down.
        from contextlib import suppress

        with suppress(Exception):
            logger.warning(
                'email_enqueue_failed', extra={'outbox_id': str(outbox.id), 'error': str(e)}
            )

    return outbox
