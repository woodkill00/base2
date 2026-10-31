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
    with db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
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
    with db_conn(tenant_id=tenant_id) as conn:  # noqa: SIM117 - close cursor before commit
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
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (user_id, tenant_id) DO NOTHING
                       RETURNING schema_version, version, theme, contrast, motion, density,
                                 locale, timezone, week_start, updated_at""",
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
                       WHERE user_id=%s AND tenant_id=%s AND version=%s
                       RETURNING schema_version, version, theme, contrast, motion, density,
                                 locale, timezone, week_start, updated_at""",
                    (
                        values['theme'], values['contrast'], values['motion'], values['density'],
                        values['locale'], values['timezone'], values['week_start'], str(user_id),
                        tenant_id, expected_version,
                    ),
                )
            if cur.rowcount != 1:
                conn.rollback()
                return None
            # Return this transaction's snapshot: a later GET could read another
            # writer's version and incorrectly let the client overwrite it.
            result = _preference_row(cur.fetchone())
            conn.commit()
    return result


def _notification_rows(rows) -> list[dict[str, Any]]:
    return [
        {'event_family': row[0], 'channel': row[1], 'delivery': row[2],
         'mandatory': row[0] in {'security', 'transactional'}, 'updated_at': row[4]}
        for row in rows
    ]


def get_notifications(*, user_id: UUID, tenant_id: str) -> dict[str, Any]:
    # One statement provides one coherent header/choice snapshot, including empty sets.
    with db_conn(tenant_id=tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT s.schema_version,s.version,p.event_family,p.channel,p.delivery,
                      p.mandatory,p.updated_at
               FROM api_notification_preference_sets s
               LEFT JOIN api_notification_preferences p
                 ON p.user_id=s.user_id AND p.tenant_id=s.tenant_id
               WHERE s.user_id=%s AND s.tenant_id=%s ORDER BY p.event_family,p.channel""",
            (str(user_id), tenant_id),
        )
        rows = cur.fetchall()
    if not rows:
        return {'schema_version': 1, 'version': 0, 'preferences': []}
    if int(rows[0][0]) != 1:
        raise ValueError('settings_schema_unsupported')
    return {'schema_version': 1, 'version': int(rows[0][1]),
            'preferences': _notification_rows([row[2:] for row in rows if row[2] is not None])}


def list_notifications(*, user_id: UUID, tenant_id: str) -> list[dict[str, Any]]:
    return get_notifications(user_id=user_id, tenant_id=tenant_id)['preferences']


def _merge_notification_choices(preferences, existing):
    mandatory_families = {'security', 'transactional'}
    choices = {}
    for row in existing:
        if row['event_family'] in mandatory_families:
            choices[(row['event_family'], row['channel'])] = {
                key: row[key] for key in ('event_family', 'channel', 'delivery')
            }
    for family in sorted(mandatory_families):
        choices.setdefault((family, 'email'), {
            'event_family': family, 'channel': 'email', 'delivery': 'immediate',
        })
    seen = set()
    for item in preferences:
        key = (item['event_family'], item['channel'])
        if (key in seen or key[0] not in {'security', 'transactional', 'product', 'marketing'}
                or key[1] not in {'email', 'in_app', 'browser'}
                or item['delivery'] not in {'immediate', 'digest', 'disabled'}):
            raise ValueError('settings_notification_invalid')
        if key[0] in mandatory_families and item['delivery'] == 'disabled':
            raise ValueError('settings_notification_mandatory')
        seen.add(key)
        choices[key] = {name: item[name] for name in ('event_family', 'channel', 'delivery')}
    return [{**choices[key], 'mandatory': key[0] in mandatory_families} for key in sorted(choices)]


def replace_notifications(
    *, user_id: UUID, tenant_id: str, expected_version: int,
    preferences: list[dict[str, Any]], ip: str = '', user_agent: str = '',
) -> dict[str, Any] | None:
    if type(expected_version) is not int or expected_version < 0:
        raise ValueError('settings_version_invalid')
    with db_conn(tenant_id=tenant_id) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ('base2-workspace-policy-v1',))
                cur.execute(
                    """SELECT version FROM api_notification_preference_sets
                       WHERE user_id=%s AND tenant_id=%s FOR UPDATE""",
                    (str(user_id), tenant_id),
                )
                row = cur.fetchone()
                if row is None:
                    if expected_version != 0:
                        conn.rollback()
                        return None
                    cur.execute(
                        """INSERT INTO api_notification_preference_sets(id,user_id,tenant_id)
                           VALUES (%s,%s,%s) ON CONFLICT (user_id, tenant_id) DO NOTHING
                           RETURNING schema_version,version""",
                        (str(uuid4()), str(user_id), tenant_id),
                    )
                else:
                    if int(row[0]) != expected_version:
                        conn.rollback()
                        return None
                    cur.execute(
                        """UPDATE api_notification_preference_sets
                           SET version=version+1,updated_at=NOW()
                           WHERE user_id=%s AND tenant_id=%s AND version=%s AND schema_version=1
                           RETURNING schema_version,version""",
                        (str(user_id), tenant_id, expected_version),
                    )
                header = cur.fetchone()
                if header is None:
                    conn.rollback()
                    return None
                cur.execute(
                    """SELECT event_family,channel,delivery,mandatory,updated_at
                       FROM api_notification_preferences WHERE user_id=%s AND tenant_id=%s
                       ORDER BY event_family,channel""", (str(user_id), tenant_id),
                )
                values = _merge_notification_choices(preferences, _notification_rows(cur.fetchall()))
                cur.execute(
                    "DELETE FROM api_notification_preferences WHERE user_id=%s AND tenant_id=%s",
                    (str(user_id), tenant_id),
                )
                for item in values:
                    cur.execute(
                        """INSERT INTO api_notification_preferences(
                               id,user_id,tenant_id,event_family,channel,delivery,mandatory
                           ) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (str(uuid4()), str(user_id), tenant_id, item['event_family'], item['channel'],
                         item['delivery'], item['mandatory']),
                    )
                cur.execute(
                    """SELECT event_family,channel,delivery,mandatory,updated_at
                       FROM api_notification_preferences WHERE user_id=%s AND tenant_id=%s
                       ORDER BY event_family,channel""", (str(user_id), tenant_id),
                )
                result: dict[str, Any] = {'schema_version': int(header[0]), 'version': int(header[1]),
                          'preferences': _notification_rows(cur.fetchall())}
                # This is the same transaction as the CAS and replacement, not a later write.
                from api.security.identity import redact_audit_metadata
                import json
                metadata = redact_audit_metadata({
                    'tenant_id': tenant_id, 'expected_version': expected_version,
                    'version': result['version'], 'preference_count': len(result['preferences']),
                })
                cur.execute(
                    """INSERT INTO api_auth_audit_events(id,user_id,action,ip,user_agent,metadata_json)
                       VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
                    (str(uuid4()), str(user_id), 'user.notification_preferences_updated',
                     ip, user_agent, json.dumps(metadata)),
                )
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


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
