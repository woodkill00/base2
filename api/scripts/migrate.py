"""Apply and verify the complete fixed API migration ledger."""

from __future__ import annotations

import json

from api.db import db_conn
from api.migrations.runner import MIGRATIONS, apply_migrations


def main() -> int:
    apply_migrations()
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute('SELECT version FROM api_schema_migrations ORDER BY version')
        applied = tuple(row[0] for row in cur.fetchall())
    if applied != MIGRATIONS:
        raise RuntimeError('api_migration_ledger_incomplete')
    print(
        json.dumps(
            {
                'migrationCount': len(applied),
                'ok': True,
                'secretValuesEmitted': 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
