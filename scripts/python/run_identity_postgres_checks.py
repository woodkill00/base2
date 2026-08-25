#!/usr/bin/env python3
"""Inner real-PostgreSQL identity checks."""
import json
from uuid import uuid4
import psycopg2
from api import db
from api.auth.repo import create_refresh_token, insert_audit_event, list_active_refresh_sessions, revoke_user_refresh_token
from api.migrations.runner import apply_migrations
from api.repositories.identity_admin import require_permission

def main():
    apply_migrations()
    user_one, user_two, org_one, org_two = uuid4(), uuid4(), uuid4(), uuid4()
    with db.db_conn() as connection, connection.cursor() as cursor:
        cursor.executemany("INSERT INTO api_auth_users(id,email,password_hash) VALUES (%s,%s,'fixture')", [(str(user_one),'one@example.test'),(str(user_two),'two@example.test')])
        cursor.executemany('INSERT INTO api_identity_organizations(id,tenant_id,name) VALUES (%s,%s,%s)', [(str(org_one),'tenant-one','One'),(str(org_two),'tenant-two','Two')])
        cursor.executemany("INSERT INTO api_identity_memberships(organization_id,user_id,role) VALUES (%s,%s,'owner')", [(str(org_one),str(user_one)),(str(org_two),str(user_two))])
        connection.commit()
    assert require_permission(user_id=user_one, tenant_id='tenant-one', permission='audit.read')
    try: require_permission(user_id=user_one, tenant_id='tenant-two', permission='audit.read')
    except PermissionError: pass
    else: raise AssertionError('cross_tenant_permission_was_granted')
    token_id, _expires_at = create_refresh_token(user_id=user_one,token_hash='a'*64,ttl_days=1,user_agent='acceptance',ip='127.0.0.1')
    assert len(list_active_refresh_sessions(user_id=user_one)) == 1
    assert revoke_user_refresh_token(user_id=user_one, token_id=token_id)
    assert list_active_refresh_sessions(user_id=user_one) == []
    insert_audit_event(user_id=user_one,action='identity.acceptance',ip='127.0.0.1',user_agent='acceptance',metadata={'tenant_id':'tenant-one'})
    with db.db_conn() as connection, connection.cursor() as cursor:
        try: cursor.execute("DELETE FROM api_auth_audit_events WHERE action='identity.acceptance'")
        except psycopg2.DatabaseError as exc:
            assert exc.pgcode == '55000'; connection.rollback()
        else: raise AssertionError('audit_delete_was_not_rejected')
    with db.db_conn(tenant_id='tenant-one') as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.tenant_id',true)"); assert cursor.fetchone()[0] == 'tenant-one'
    with db.db_conn() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.tenant_id',true)"); assert cursor.fetchone()[0] in (None,'')
    db.close_pool()
    print(json.dumps({'status':'passed','database':'postgres:16-alpine','tenantCount':2,'crossTenantDenied':True,'sessionRevoked':True,'auditAppendOnly':True,'poolTenantReset':True},sort_keys=True))

if __name__ == '__main__': main()
