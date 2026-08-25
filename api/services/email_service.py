from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from api.db import db_conn
from api.services.transactional_email import (
    DisabledEmailAdapter,
    LocalFakeEmailAdapter,
    RenderedEmail,
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
                INSERT INTO api_email_outbox(id, to_email, subject, body_text, body_html)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, to_email, subject, body_text, body_html, status, provider, provider_message_id, error, created_at, sent_at
                """,
                (str(outbox_id), to_email, subject, body_text, body_html or ''),
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
    )


def get_outbox_email(outbox_id: UUID) -> EmailOutboxRow | None:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, to_email, subject, body_text, body_html, status, provider, provider_message_id, error, created_at, sent_at
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
    )


def mark_outbox_sent(
    *,
    outbox_id: UUID,
    provider: str = 'local_outbox',
    provider_message_id: str = 'local',
) -> None:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_email_outbox
                SET status='sent', sent_at=NOW(), provider=%s, provider_message_id=%s, error=''
                WHERE id=%s
                """,
                (provider, provider_message_id or '', str(outbox_id)),
            )


def mark_outbox_failed(*, outbox_id: UUID, error: str) -> None:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_email_outbox
                SET status='failed', error=%s
                WHERE id=%s
                """,
                (error[:2000], str(outbox_id)),
            )


def mark_outbox_status(
    *, outbox_id: UUID, status: str, provider: str, provider_message_id: str = '', error: str = ''
) -> None:
    if status not in {'queued', 'sent', 'disabled', 'suppressed', 'retry', 'dead_letter'}:
        raise ValueError('outbox_status_invalid')
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_email_outbox
                SET status=%s, provider=%s, provider_message_id=%s, error=%s,
                    sent_at=CASE WHEN %s='sent' THEN NOW() ELSE sent_at END
                WHERE id=%s
                """,
                (status, provider, provider_message_id[:255], error[:2000], status, str(outbox_id)),
            )


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
    if mode != 'disabled':
        raise RuntimeError('email_adapter_not_allowed')
    return DisabledEmailAdapter()


def process_outbox_email(*, outbox_id: UUID) -> None:
    """Process an outbox row.

    For now, this is a staging-safe "local outbox" sender: it marks the email as sent
    without requiring SMTP configuration.
    """

    existing = get_outbox_email(outbox_id)
    if existing is None:
        raise RuntimeError('outbox_not_found')

    if existing.sent_at is not None or existing.status == 'sent':
        return

    adapter = _configured_adapter()
    result = deliver_email(
        RenderedEmail(
            kind='outbox',
            recipient=existing.to_email,
            subject=existing.subject,
            text=existing.body_text,
            html=existing.body_html,
        ),
        adapter,
    )
    mark_outbox_status(
        outbox_id=outbox_id,
        status=result.status,
        provider=result.provider,
        provider_message_id=result.message_id,
        error='' if result.status == 'sent' else f'delivery_{result.status}',
    )


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
