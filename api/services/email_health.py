"""Worker-owned deployment health, without recipient data or sending authority.

Only the email worker queries the global outbox. Operations readers receive a
closed service-status code, never counts or tenant/message identifiers. A healthy
transport observation is not evidence of inbox delivery.
"""

import json
import os
from datetime import UTC, datetime

from api import redis_client

CODES = frozenset(
    {
        'email.transport-ready',
        'email.outbox-attention',
        'email.not-configured',
        'email.observation-failed',
    }
)


def _configuration_ready() -> bool:
    from api.services.email_service import _configured_adapter

    try:
        return _configured_adapter().name in {'resend', 'smtp', 'local_fake'}
    except Exception:
        return False


def _outbox_requires_attention() -> bool:
    from api.db import db_conn

    with db_conn() as connection, connection.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout = '2000ms'")
        cursor.execute("""SELECT EXISTS (
            SELECT 1 FROM api_email_outbox
            WHERE status IN ('dead_letter', 'failed')
               OR (status IN ('queued', 'sending', 'retry', 'disabled')
                   AND created_at < NOW() - INTERVAL '10 minutes')
        )""")
        row = cursor.fetchone()
        if row is None or type(row[0]) is not bool:
            raise RuntimeError('email_health_query_invalid')
        return row[0]


def publish_email_health(*, now: datetime | None = None) -> None:
    current = now or datetime.now(UTC)
    failed = False
    try:
        code = (
            'email.not-configured'
            if not _configuration_ready()
            else 'email.outbox-attention'
            if _outbox_requires_attention()
            else 'email.transport-ready'
        )
    except Exception:
        code, failed = 'email.observation-failed', True
    payload = {
        'observedAt': current.isoformat(),
        'deploymentEpoch': os.environ.get('BASE2_DEPLOYMENT_EPOCH', 'development'),
        'code': code,
    }
    try:
        published = redis_client.get_client().set(
            redis_client.key('operations', 'email-health'), json.dumps(payload), ex=180
        )
        if not published:
            raise RuntimeError('email_health_publication_failed')
    except Exception:
        raise RuntimeError('email_health_publication_failed') from None
    if failed:
        raise RuntimeError('email_health_observation_failed') from None


def email_health_probe(*, now: datetime | None = None) -> tuple[str, str, int]:
    try:
        raw = redis_client.get_client().get(redis_client.key('operations', 'email-health'))
        if not isinstance(raw, (str, bytes)) or len(raw) > 4096:
            raise ValueError('invalid observation')
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {'observedAt', 'deploymentEpoch', 'code'}:
            raise ValueError('invalid observation')
        age = (
            (now or datetime.now(UTC)) - datetime.fromisoformat(value['observedAt'])
        ).total_seconds()
        if (
            not 0 <= age <= 120
            or value['deploymentEpoch'] != os.environ.get('BASE2_DEPLOYMENT_EPOCH', 'development')
            or value['code'] not in CODES
        ):
            raise ValueError('invalid observation')
        code = value['code']
        return ('healthy' if code == 'email.transport-ready' else 'degraded', code, 0)
    except Exception:
        return 'degraded', 'email.observation-stale', 0
