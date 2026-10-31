#!/usr/bin/env python3
"""Inner real-PostgreSQL identity checks."""
import json
from uuid import uuid4

import psycopg2

from api import db
from api.auth.repo import (
    create_refresh_token,
    insert_audit_event,
    list_active_refresh_sessions,
    revoke_user_refresh_token,
)
from api.migrations.runner import apply_migrations
from api.repositories.identity_admin import admin_overview, require_permission
from api.repositories.settings import security_events


def check_organization_audit_scope(user_one, user_two, org_one, org_two):
    """Prove JSONB scope independently of current actor memberships on Postgres."""
    with db.db_conn() as connection, connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO api_identity_memberships(organization_id,user_id,role) VALUES (%s,%s,'admin')",
            [(str(org_two), str(user_one)), (str(org_one), str(user_two))],
        )
        connection.commit()

    scope_one = {'tenant_id': 'tenant-one', 'organization_id': str(org_one)}
    scope_two = {'tenant_id': 'tenant-two', 'organization_id': str(org_two)}
    fixtures = [
        (user_one, 'identity.scope_one', {
            **scope_one, 'secret': 'fixture-private-secret',
            'nested': {'token': 'fixture-private-token', 'safe': 'retained'},
        }),
        (user_one, 'identity.scope_two', scope_two),
        (user_two, 'identity.departed_member', scope_one),
        (user_one, 'auth.personal_activity', {}),
        (user_two, 'auth.other_personal_activity', {}),
        (user_one, 'identity.legacy_unscoped', {}),
        (user_one, 'identity.legacy_tenant_only', {'tenant_id': 'tenant-one'}),
        (user_one, 'identity.legacy_org_only', {'organization_id': str(org_one)}),
        (user_one, 'identity.wrong_org', {**scope_one, 'organization_id': str(org_two)}),
        (user_one, 'identity.wrong_tenant', {**scope_one, 'tenant_id': 'tenant-two'}),
        (user_one, 'identity.similar_tenant', {**scope_one, 'tenant_id': 'tenant-one-extra'}),
    ]
    for actor, action, metadata in fixtures:
        insert_audit_event(
            user_id=actor, action=action, ip='', user_agent='acceptance', metadata=metadata,
        )

    expected_one = {'identity.scope_one', 'identity.departed_member'}
    audit_one = admin_overview(user_id=user_one, tenant_id='tenant-one')['audit']
    assert {event['action'] for event in audit_one} == expected_one
    assert {event['action'] for event in admin_overview(user_id=user_one, tenant_id='tenant-two')['audit']} == {'identity.scope_two'}
    redacted = next(event['metadata'] for event in audit_one if event['action'] == 'identity.scope_one')
    assert redacted['secret'] == '[REDACTED]'
    assert redacted['nested'] == {'token': '[REDACTED]', 'safe': 'retained'}
    assert 'fixture-private-' not in json.dumps(audit_one, default=str)

    # Removing a member must neither erase correctly scoped history nor cause
    # their unrelated account activity to become organization-visible.
    with db.db_conn() as connection, connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM api_auth_audit_events')
        count_before = cursor.fetchone()[0]
        cursor.execute(
            'DELETE FROM api_identity_memberships WHERE organization_id=%s AND user_id=%s',
            (str(org_one), str(user_two)),
        )
        connection.commit()
    assert {event['action'] for event in admin_overview(user_id=user_one, tenant_id='tenant-one')['audit']} == expected_one
    with db.db_conn() as connection, connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM api_auth_audit_events')
        assert cursor.fetchone()[0] == count_before

    personal = {event['action'] for event in security_events(user_id=user_one, limit=50)}
    assert personal == {action for actor, action, _metadata in fixtures if actor == user_one}


def main():
    apply_migrations()
    user_one, user_two, org_one, org_two = uuid4(), uuid4(), uuid4(), uuid4()
    with db.db_conn() as connection, connection.cursor() as cursor:
        cursor.executemany("INSERT INTO api_auth_users(id,email,password_hash) VALUES (%s,%s,'fixture')", [(str(user_one),'one@example.test'),(str(user_two),'two@example.test')])
        cursor.executemany('INSERT INTO api_identity_organizations(id,tenant_id,name) VALUES (%s,%s,%s)', [(str(org_one),'tenant-one','One'),(str(org_two),'tenant-two','Two')])
        cursor.executemany("INSERT INTO api_identity_memberships(organization_id,user_id,role) VALUES (%s,%s,'owner')", [(str(org_one),str(user_one)),(str(org_two),str(user_two))])
        connection.commit()
    assert require_permission(user_id=user_one, tenant_id='tenant-one', permission='audit.read')
    try:
        require_permission(user_id=user_one, tenant_id='tenant-two', permission='audit.read')
    except PermissionError:
        pass
    else:
        raise AssertionError('cross_tenant_permission_was_granted')
    check_organization_audit_scope(user_one, user_two, org_one, org_two)
    token_id, _expires_at = create_refresh_token(user_id=user_one,token_hash='a'*64,ttl_days=1,user_agent='acceptance',ip='127.0.0.1')
    assert len(list_active_refresh_sessions(user_id=user_one)) == 1
    assert revoke_user_refresh_token(user_id=user_one, token_id=token_id)
    assert list_active_refresh_sessions(user_id=user_one) == []
    insert_audit_event(user_id=user_one,action='identity.acceptance',ip='127.0.0.1',user_agent='acceptance',metadata={'tenant_id':'tenant-one'})
    with db.db_conn() as connection, connection.cursor() as cursor:
        try:
            cursor.execute("DELETE FROM api_auth_audit_events WHERE action='identity.acceptance'")
        except psycopg2.DatabaseError as exc:
            assert exc.pgcode == '55000'
            connection.rollback()
        else:
            raise AssertionError('audit_delete_was_not_rejected')
    with db.db_conn(tenant_id='tenant-one') as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.tenant_id',true)")
        assert cursor.fetchone()[0] == 'tenant-one'
    with db.db_conn() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.tenant_id',true)")
        assert cursor.fetchone()[0] in (None,'')
        cursor.execute('SHOW server_version')
        server_version = cursor.fetchone()[0]
    db.close_pool()
    print(json.dumps({'status':'passed','database':'postgresql','serverVersion':server_version,'tenantCount':2,'crossTenantDenied':True,'sessionRevoked':True,'auditAppendOnly':True,'poolTenantReset':True,'organizationAuditScope':True,'departedMemberAuditRetained':True,'personalAuditPreserved':True},sort_keys=True))

if __name__ == '__main__':
    main()
