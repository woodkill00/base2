from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from api.db import db_conn


DEFAULTS: dict[str, Any] = {
    'schema_version': 1,
    'version': 0,
    'theme': 'system',
    'contrast': 'system',
    'motion': 'system',
    'density': 'comfortable',
    'locale': 'en',
    'timezone': 'UTC',
    'week_start': 'system',
}


def _preference_row(row) -> dict[str, Any]:
    if row is None:
        return dict(DEFAULTS)
    return {
        'schema_version': int(row[0]), 'version': int(row[1]), 'theme': row[2],
        'contrast': row[3], 'motion': row[4], 'density': row[5], 'locale': row[6],
        'timezone': row[7], 'week_start': row[8], 'updated_at': row[9],
    }


def get_preferences(*, user_id: UUID, tenant_id: str) -> dict[str, Any]:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT schema_version, version, theme, contrast, motion, density,
                      locale, timezone, week_start, updated_at
               FROM api_user_preferences WHERE user_id=%s AND tenant_id=%s""",
            (str(user_id), tenant_id),
        )
        return _preference_row(cur.fetchone())


def update_preferences(
    *, user_id: UUID, tenant_id: str, expected_version: int, values: dict[str, str]
) -> dict[str, Any] | None:
    with db_conn() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version FROM api_user_preferences WHERE user_id=%s AND tenant_id=%s FOR UPDATE",
                (str(user_id), tenant_id),
            )
            row = cur.fetchone()
            if row is None:
                if expected_version != 0:
                    conn.rollback()
                    return None
                cur.execute(
                    """INSERT INTO api_user_preferences(
                           id,user_id,tenant_id,theme,contrast,motion,density,locale,timezone,week_start
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        str(uuid4()), str(user_id), tenant_id, values['theme'], values['contrast'],
                        values['motion'], values['density'], values['locale'], values['timezone'],
                        values['week_start'],
                    ),
                )
            else:
                if int(row[0]) != expected_version:
                    conn.rollback()
                    return None
                cur.execute(
                    """UPDATE api_user_preferences
                       SET theme=%s,contrast=%s,motion=%s,density=%s,locale=%s,timezone=%s,
                           week_start=%s,version=version+1,updated_at=NOW()
                       WHERE user_id=%s AND tenant_id=%s AND version=%s""",
                    (
                        values['theme'], values['contrast'], values['motion'], values['density'],
                        values['locale'], values['timezone'], values['week_start'], str(user_id),
                        tenant_id, expected_version,
                    ),
                )
                if cur.rowcount != 1:
                    conn.rollback()
                    return None
            conn.commit()
    return get_preferences(user_id=user_id, tenant_id=tenant_id)


def list_notifications(*, user_id: UUID, tenant_id: str) -> list[dict[str, Any]]:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT event_family,channel,delivery,mandatory,updated_at
               FROM api_notification_preferences WHERE user_id=%s AND tenant_id=%s
               ORDER BY event_family,channel""",
            (str(user_id), tenant_id),
        )
        return [
            {'event_family': row[0], 'channel': row[1], 'delivery': row[2],
             'mandatory': bool(row[3]), 'updated_at': row[4]}
            for row in cur.fetchall()
        ]


def replace_notifications(
    *, user_id: UUID, tenant_id: str, preferences: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    with db_conn() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM api_notification_preferences WHERE user_id=%s AND tenant_id=%s",
                (str(user_id), tenant_id),
            )
            for item in preferences:
                cur.execute(
                    """INSERT INTO api_notification_preferences(
                           id,user_id,tenant_id,event_family,channel,delivery,mandatory
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (str(uuid4()), str(user_id), tenant_id, item['event_family'], item['channel'],
                     item['delivery'], bool(item['mandatory'])),
                )
            conn.commit()
    return list_notifications(user_id=user_id, tenant_id=tenant_id)


def security_events(*, user_id: UUID, limit: int = 25) -> list[dict[str, Any]]:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id,action,created_at,user_agent
               FROM api_auth_audit_events
               WHERE user_id=%s AND (action LIKE 'identity.%%' OR action LIKE 'auth.%%' OR action LIKE 'user.%%')
               ORDER BY created_at DESC LIMIT %s""",
            (str(user_id), max(1, min(int(limit), 50))),
        )
        return [
            {'id': str(row[0]), 'action': row[1], 'created_at': row[2],
             'device': (str(row[3] or '')[:120] or 'Unknown device')}
            for row in cur.fetchall()
        ]
