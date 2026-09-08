"""Durable tenant-lifecycle replay protection."""

from __future__ import annotations

import re
from datetime import datetime

from api.db import workspace_db_conn

NONCE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')


def consume_destructive_approval_nonce(
    tenant_id: str,
    nonce: str,
    approval_digest: str,
    expires_at: datetime,
) -> bool:
    """Atomically consume an approval once, durably and tenant-scoped."""
    if (
        not tenant_id
        or not NONCE.fullmatch(nonce or '')
        or not DIGEST.fullmatch(approval_digest or '')
        or expires_at.tzinfo is None
    ):
        return False
    with workspace_db_conn(tenant_id=tenant_id) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO sitecontent_destructiveapprovaluse
                     (id,site_id,nonce,approval_digest,expires_at,consumed_at,created_at,updated_at)
                   SELECT gen_random_uuid(),%s,%s,%s,%s,NOW(),NOW(),NOW()
                   WHERE %s>NOW()
                   ON CONFLICT (site_id,nonce) DO NOTHING""",
                (tenant_id, nonce, approval_digest, expires_at, expires_at),
            )
            consumed = cursor.rowcount == 1
        conn.commit()
    return consumed
