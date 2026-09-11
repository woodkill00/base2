"""Opt-in preview application owner; never a seed-password reset."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
from uuid import uuid4

from api.auth.passwords import hash_password
from api.auth.service import _validate_password_or_raise
from api.db import db_conn
from api.site_manifest import load_runtime_manifest


def ensure_owner(*, email: str, password: str, display_name: str, profile: str) -> str:
    manifest, _ = load_runtime_manifest()
    if profile != 'base2-obsidian' or manifest['siteId'] != profile:
        raise ValueError('owner_environment_mismatch')
    email = email.strip().lower()
    if len(email) > 254 or email.count('@') != 1 or any(c.isspace() for c in email):
        raise ValueError('owner_email_invalid')
    if not display_name.strip() or len(display_name) > 80:
        raise ValueError('owner_name_invalid')
    _validate_password_or_raise(password)
    with db_conn() as conn:
        with conn.cursor() as cur:
            # Serialize only provisioning of this exact identity. Password/state
            # of existing users are NEVER overwritten, including disabled users.
            cur.execute(
                'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', ('owner:' + profile,)
            )
            cur.execute(
                'SELECT email,display_name,is_active FROM api_auth_users WHERE email=%s OR display_name=%s FOR UPDATE',
                (email, display_name),
            )
            rows = cur.fetchall()
            if rows:
                if (
                    len(rows) != 1
                    or rows[0][0] != email
                    or rows[0][1] != display_name
                    or not rows[0][2]
                ):
                    raise ValueError('owner_identity_conflict')
                return 'existing-preserved'
            cur.execute(
                'INSERT INTO api_auth_users(id,email,password_hash,display_name) VALUES (%s,%s,%s,%s)',
                (str(uuid4()), email, hash_password(password), display_name),
            )
        conn.commit()
    return 'created'


def main() -> int:
    if os.environ.get('BASE2_OWNER_ENABLED') != 'true':
        print(json.dumps({'status': 'disabled'}))
        return 0
    try:
        if sys.argv[1:] == ['--stdin']:
            raw = sys.stdin.read(16385)
            if len(raw) > 16384:
                raise ValueError('owner_configuration_too_large')
        elif not sys.argv[1:]:
            path = Path(os.environ['BASE2_OWNER_FILE'])
            info = path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) & 0o077
                or info.st_size > 16384
            ):
                raise ValueError('owner_file_not_private')
            raw = path.read_text()
        else:
            raise ValueError('owner_arguments_invalid')
        config = json.loads(raw)
        if set(config) != {'email', 'password', 'display_name', 'profile'}:
            raise ValueError('owner_configuration_invalid')
        status = ensure_owner(**config)
    except Exception:
        # Do not print exception strings/tracebacks containing driver parameters.
        print(json.dumps({'status': 'blocked', 'reason': 'owner_provisioning_failed'}))
        return 1
    print(json.dumps({'status': status, 'credentialsChanged': False, 'privilegeElevation': False}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
