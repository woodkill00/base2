"""Apply and verify the complete fixed API migration ledger."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from api.db import db_conn
from api.migrations.runner import MIGRATIONS, apply_migrations


def main(argv: Sequence[str] | None = ()) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify without applying migrations')
    args = parser.parse_args(argv)
    if not args.check:
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
    raise SystemExit(main(None))
