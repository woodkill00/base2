"""Exercise audit predicates with SQL, not a cursor that invents filtered results.

SQLite executes the read predicates in these self-contained tests. PostgreSQL
JSONB and append-only enforcement require the real identity acceptance gate;
restricted-role RLS still requires the separate production-like integration gate.
"""

import json
import sqlite3
from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from api.auth import repo as auth_repository
from api.repositories import identity_admin as repository
from api.repositories import settings as settings_repository

USER_ID = UUID('00000000-0000-0000-0000-000000000611')
FORMER_MEMBER_ID = UUID('00000000-0000-0000-0000-000000000612')
ORG_A = UUID('00000000-0000-0000-0000-000000000621')
ORG_B = UUID('00000000-0000-0000-0000-000000000622')


@pytest.fixture
def audit_database(monkeypatch):
    database = sqlite3.connect(':memory:')
    database.create_function('NOW', 0, lambda: '2026-10-30T12:00:00')
    database.executescript('''
        CREATE TABLE api_auth_users (id TEXT, email TEXT);
        CREATE TABLE api_identity_organizations (id TEXT, tenant_id TEXT, name TEXT);
        CREATE TABLE api_identity_memberships (
            organization_id TEXT, user_id TEXT, role TEXT, status TEXT, updated_at TEXT
        );
        CREATE TABLE api_identity_invitations (
            id TEXT, organization_id TEXT, email TEXT, role TEXT, expires_at TEXT,
            accepted_at TEXT, revoked_at TEXT, created_at TEXT
        );
        CREATE TABLE api_identity_credentials (
            id TEXT, organization_id TEXT, label TEXT, prefix TEXT, scopes TEXT,
            created_at TEXT, last_used_at TEXT, revoked_at TEXT
        );
        CREATE TABLE api_auth_audit_events (
            id TEXT, user_id TEXT, action TEXT, ip TEXT, user_agent TEXT,
            metadata_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    database.executemany(
        'INSERT INTO api_auth_users VALUES (?, ?)',
        [(str(USER_ID), 'owner@example.test'), (str(FORMER_MEMBER_ID), 'former@example.test')],
    )
    database.executemany(
        'INSERT INTO api_identity_organizations VALUES (?, ?, ?)',
        [(str(ORG_A), 'tenant-a', 'A'), (str(ORG_B), 'tenant-b', 'B')],
    )
    database.executemany(
        'INSERT INTO api_identity_memberships VALUES (?, ?, ?, ?, ?)',
        [(str(org), str(USER_ID), 'owner', 'active', '2026-10-30') for org in (ORG_A, ORG_B)],
    )
    calls = []

    class Cursor:
        def __enter__(self):
            self.cursor = database.cursor()
            return self

        def __exit__(self, *_args):
            self.cursor.close()

        def execute(self, query, params=()):
            calls.append((query, params))
            self.query = query
            # These are driver/dialect adaptations only: the production WHERE
            # predicates, joins, ordering, and limit are executed unchanged.
            self.cursor.execute(query.replace('%s', '?').replace('::jsonb', ''), params)

        def fetchone(self):
            return self.cursor.fetchone()

        def fetchall(self):
            rows = self.cursor.fetchall()
            if 'SELECT id, action, created_at, metadata_json' in self.query:
                return [(*row[:3], json.loads(row[3])) for row in rows]
            return rows

    class Connection:
        autocommit = False

        def cursor(self):
            return Cursor()

    @contextmanager
    def db_conn(**kwargs):
        assert not kwargs or kwargs['tenant_id'] in {'tenant-a', 'tenant-b'}
        yield Connection()

    for module in (repository, auth_repository, settings_repository):
        monkeypatch.setattr(module, 'db_conn', db_conn)

    def insert(*, actor=USER_ID, metadata=None, action='identity.invitation_created', order=0):
        event_id = str(uuid4())
        database.execute(
            'INSERT INTO api_auth_audit_events VALUES (?, ?, ?, ?, ?, ?, ?)',
            (event_id, str(actor) if actor else None, action, '', 'fixture',
             json.dumps(metadata), f'2026-10-30T12:{order:02d}:00'),
        )
        return event_id

    yield database, insert, calls
    database.close()


def audit_ids(tenant_id):
    return [
        event['id']
        for event in repository.admin_overview(user_id=USER_ID, tenant_id=tenant_id)['audit']
    ]


def test_dual_member_sees_only_exact_organization_and_tenant_events(audit_database):
    _database, insert, calls = audit_database
    event_a = insert(metadata={'tenant_id': 'tenant-a', 'organization_id': str(ORG_A)})
    event_b = insert(metadata={'tenant_id': 'tenant-b', 'organization_id': str(ORG_B)})
    # Each half of the boundary must match independently; membership is not
    # evidence that an event belongs to the organization currently being read.
    insert(metadata={'tenant_id': 'tenant-a', 'organization_id': str(ORG_B)})
    insert(metadata={'tenant_id': 'tenant-b', 'organization_id': str(ORG_A)})
    insert(metadata={'tenant_id': 'tenant-a-extra', 'organization_id': str(ORG_A)})
    assert audit_ids('tenant-a') == [event_a]
    assert audit_ids('tenant-b') == [event_b]
    assert all(query.lstrip().startswith('SELECT') for query, _params in calls)


@pytest.mark.parametrize('metadata', [
    None, {}, {'organization_id': str(ORG_A)}, {'tenant_id': 'tenant-a'},
    {'tenant_id': None, 'organization_id': str(ORG_A)},
    {'tenant_id': 'tenant-a', 'organization_id': None},
    {'scope': {'tenant_id': 'tenant-a', 'organization_id': str(ORG_A)}},
])
def test_unscoped_or_partial_legacy_audit_is_not_reassigned_to_org(audit_database, metadata):
    _database, insert, _calls = audit_database
    insert(metadata=metadata)
    assert audit_ids('tenant-a') == []


def test_account_security_events_stay_personal_and_account_wide(audit_database):
    _database, insert, _calls = audit_database
    account_event = insert(metadata={}, action='auth.login')
    mfa_event = insert(metadata={}, action='identity.totp_enabled')
    org_a_event = insert(metadata={'tenant_id': 'tenant-a', 'organization_id': str(ORG_A)})
    org_b_event = insert(metadata={'tenant_id': 'tenant-b', 'organization_id': str(ORG_B)})
    insert(actor=FORMER_MEMBER_ID, metadata={}, action='auth.login')
    assert audit_ids('tenant-a') == [org_a_event]
    assert {
        event['id'] for event in settings_repository.security_events(user_id=USER_ID)
    } == {account_event, mfa_event, org_a_event, org_b_event}


def test_scoped_history_survives_member_removal(audit_database):
    database, insert, _calls = audit_database
    database.execute(
        'INSERT INTO api_identity_memberships VALUES (?, ?, ?, ?, ?)',
        (str(ORG_A), str(FORMER_MEMBER_ID), 'admin', 'active', '2026-10-30'),
    )
    event = insert(
        actor=FORMER_MEMBER_ID,
        metadata={'tenant_id': 'tenant-a', 'organization_id': str(ORG_A)},
    )
    assert audit_ids('tenant-a') == [event]
    database.execute('DELETE FROM api_identity_memberships WHERE user_id=?', (str(FORMER_MEMBER_ID),))
    assert audit_ids('tenant-a') == [event]


def test_audit_limit_is_applied_after_exact_scope_filter(audit_database):
    _database, insert, _calls = audit_database
    older = insert(metadata={'tenant_id': 'tenant-a', 'organization_id': str(ORG_A)}, order=1)
    newer = insert(metadata={'tenant_id': 'tenant-a', 'organization_id': str(ORG_A)}, order=2)
    for _ in range(105):
        insert(metadata={'tenant_id': 'tenant-b', 'organization_id': str(ORG_B)}, order=3)
    assert audit_ids('tenant-a') == [newer, older]
    assert len(audit_ids('tenant-b')) == 100


def test_scoped_audit_insert_preserves_redaction_without_rewriting_history(audit_database):
    database, insert, calls = audit_database
    legacy_id = insert(metadata={'secret': 'legacy-private-value'})
    auth_repository.insert_audit_event(
        user_id=USER_ID, action='identity.credential_created', ip='', user_agent='fixture',
        metadata={
            'tenant_id': 'tenant-a', 'organization_id': str(ORG_A),
            'secret': 'private-secret', 'password': 'private-password',
            'nested': {'token': 'private-token', 'safe': 'kept'},
            'items': [{'recovery_code': 'private-recovery'}],
        },
    )
    audit = repository.admin_overview(user_id=USER_ID, tenant_id='tenant-a')['audit']
    assert len(audit) == 1
    assert audit[0]['metadata'] == {
        'tenant_id': 'tenant-a', 'organization_id': str(ORG_A),
        'secret': '[REDACTED]', 'password': '[REDACTED]',
        'nested': {'token': '[REDACTED]', 'safe': 'kept'},
        'items': [{'recovery_code': '[REDACTED]'}],
    }
    assert 'private-' not in json.dumps(audit)
    assert database.execute(
        'SELECT metadata_json FROM api_auth_audit_events WHERE id=?', (legacy_id,),
    ).fetchone() == (json.dumps({'secret': 'legacy-private-value'}),)
    assert not any(query.lstrip().startswith(('UPDATE', 'DELETE')) for query, _params in calls)
