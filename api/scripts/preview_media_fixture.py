"""Opt-in, one-shot synthetic media membership for an owned ephemeral preview.

Invoked only through authenticated operator exec, never an HTTP endpoint. Refuse
an existing organization or account; do not modify real users or global grants.
The entire fixture transaction rolls back on any collision/error.
"""

from datetime import UTC, datetime, timedelta
import json
import os
import re
import sys
from uuid import uuid4

from api.auth.passwords import hash_password
from api.auth.service import _validate_password_or_raise
from api.db import db_conn
from api.site_manifest import load_runtime_manifest


def provision(config, *, now=None):
    now = now or datetime.now(UTC)
    if not isinstance(config, dict) or set(config) != {'run_id', 'expires_at', 'password'}:
        raise ValueError('preview_fixture_invalid')
    run_id = config['run_id']
    if not isinstance(run_id, str) or not re.fullmatch(r'base2-full-\d{8}-\d{6}', run_id):
        raise ValueError('preview_fixture_invalid')
    expiry = datetime.fromisoformat(config['expires_at'].replace('Z', '+00:00'))
    if expiry.tzinfo is None or not now < expiry <= now + timedelta(hours=1):
        raise ValueError('preview_fixture_expired')
    manifest, _ = load_runtime_manifest()
    if manifest['siteId'] != 'base2-obsidian':
        raise ValueError('preview_fixture_profile')
    _validate_password_or_raise(config['password'])
    email = f'media-{run_id}@example.invalid'
    user_id, organization_id = str(uuid4()), str(uuid4())
    with db_conn(tenant_id='base2-obsidian') as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(hashtext(%s))', ('identity:base2-obsidian',)
            )
            cursor.execute(
                'SELECT id FROM api_identity_organizations WHERE tenant_id=%s', ('base2-obsidian',)
            )
            if cursor.fetchone():
                raise ValueError('preview_fixture_existing_organization')
            cursor.execute('SELECT id FROM api_auth_users WHERE email=%s', (email,))
            if cursor.fetchone():
                raise ValueError('preview_fixture_existing_user')
            cursor.execute(
                'INSERT INTO api_auth_users(id,email,password_hash,display_name) VALUES (%s,%s,%s,%s)',
                (user_id, email, hash_password(config['password']), 'Preview media fixture'),
            )
            cursor.execute(
                'INSERT INTO api_identity_organizations(id,tenant_id,name) VALUES (%s,%s,%s)',
                (organization_id, 'base2-obsidian', f'Preview fixture {run_id}'),
            )
            cursor.execute(
                "INSERT INTO api_identity_memberships(organization_id,user_id,role,status) VALUES (%s,%s,'editor','active')",
                (organization_id, user_id),
            )
        connection.commit()
    return {'status': 'created', 'role': 'editor', 'secretValuesEmitted': 0}


def main():
    if os.environ.get('BASE2_PREVIEW_MEDIA_FIXTURE') != 'true':
        print(json.dumps({'status': 'disabled'}))
        return 1
    try:
        if sys.argv[1:]:
            raise ValueError('preview_fixture_arguments')
        raw = sys.stdin.read(4097)
        if len(raw) > 4096:
            raise ValueError('preview_fixture_size')
        result = provision(json.loads(raw))
    except Exception:
        print(json.dumps({'status': 'blocked', 'secretValuesEmitted': 0}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
