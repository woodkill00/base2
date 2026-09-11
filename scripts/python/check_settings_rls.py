"""Readiness drill: real runtime-role RLS; all synthetic changes rolled back."""
from contextlib import contextmanager
import json
from uuid import uuid4

from api.db import db_conn

from api.repositories import settings as repo

with db_conn() as conn:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")
            assert cur.fetchone() == (False, False), 'test requires actual restricted runtime role'
            user, other = uuid4(), uuid4()
            for uid in (user, other):
                cur.execute("INSERT INTO api_auth_users(id,email,password_hash) VALUES (%s,%s,%s)",
                            (str(uid), str(uid) + '@example.test', 'disabled-synthetic-hash'))
        class Transaction:
            def cursor(self): return conn.cursor()
            def commit(self): pass  # Preserve outer rollback-only test transaction.
            def rollback(self): raise AssertionError('unexpected rollback during success drill')
        @contextmanager
        def scope(*, tenant_id=None):
            assert tenant_id, 'repository omitted required tenant context'
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id',%s,true)", (tenant_id,))
            yield Transaction()
        repo.db_conn = scope
        values = {k: v for k, v in repo.DEFAULTS.items() if k not in ('schema_version','version')}
        result = repo.update_preferences(user_id=user, tenant_id='base2-obsidian', expected_version=0, values=values)
        assert result['version'] == 1
        assert repo.get_preferences(user_id=other, tenant_id='base2-obsidian')['version'] == 0
        assert repo.get_preferences(user_id=user, tenant_id='another-tenant')['version'] == 0
        assert repo.get_preferences(user_id=user, tenant_id='base2-obsidian')['version'] == 1
        result = repo.replace_notifications(user_id=user, tenant_id='base2-obsidian',
                    preferences=[dict(event_family='security',channel='email',delivery='immediate',mandatory=True)])
        assert len(result) == 1
        assert repo.list_notifications(user_id=other, tenant_id='base2-obsidian') == []
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id','another-tenant',true)")
            cur.execute("SELECT count(*) FROM api_user_preferences WHERE user_id=%s", (str(user),))
            assert cur.fetchone()[0] == 0
    finally:
        conn.rollback()
print(json.dumps({'runtimeRoleRestricted': True, 'settingsRoundTrip': True,
                  'tenantAndUserIsolation': True, 'syntheticChangesRolledBack': True}))
