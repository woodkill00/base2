from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

import pytest

from api.repositories import identity_admin as repository


USER_ID = UUID('00000000-0000-0000-0000-000000000511')
ORG_ID = UUID('00000000-0000-0000-0000-000000000522')
RECORD_ID = UUID('00000000-0000-0000-0000-000000000533')


class FakeCursor:
    def __init__(self, *, membership_row=None, activate_count=1):
        self.membership_row = membership_row
        self.activate_count = activate_count
        self.rowcount = 0
        self.query = ''
        self.params = ()
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=()):
        self.query = ' '.join(query.split())
        self.params = params
        self.calls.append((self.query, params))
        self.rowcount = self.activate_count if 'SET is_active=TRUE' in self.query else 1

    def fetchone(self):
        if 'FROM api_identity_organizations' in self.query:
            return self.membership_row
        if 'SELECT secret_ciphertext' in self.query:
            return ('ciphertext',)
        return None

    def fetchall(self):
        if 'FROM api_identity_invitations' in self.query:
            return [(RECORD_ID, 'invite@example.test', 'editor', datetime.now(timezone.utc))]
        if 'JOIN api_auth_users' in self.query:
            return [(USER_ID, 'owner@example.test', 'owner', 'active', datetime.now(timezone.utc))]
        if 'FROM api_identity_credentials' in self.query:
            return [(RECORD_ID, 'automation', 'b2_abcd', ['content.read'], None, None)]
        if 'FROM api_auth_audit_events' in self.query:
            return [(RECORD_ID, 'identity.invitation_created', None, {})]
        return []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.autocommit = False
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def install_db(monkeypatch, *, membership=True, activate_count=1):
    row = (ORG_ID, 'tenant-a', 'Tenant A', 'owner') if membership else None
    cursor = FakeCursor(membership_row=row, activate_count=activate_count)
    connection = FakeConnection(cursor)

    @contextmanager
    def fake_db_conn(**kwargs):
        if kwargs:
            assert kwargs == {'tenant_id': 'tenant-a'}
        yield connection

    monkeypatch.setattr(repository, 'db_conn', fake_db_conn)
    return connection, cursor


def test_membership_permission_and_generic_denial(monkeypatch):
    install_db(monkeypatch)
    member = repository.membership(user_id=USER_ID, tenant_id='tenant-a')
    assert member == {
        'organization_id': ORG_ID,
        'tenant_id': 'tenant-a',
        'name': 'Tenant A',
        'role': 'owner',
    }
    assert repository.require_permission(
        user_id=USER_ID, tenant_id='tenant-a', permission='credential.create'
    ) == member

    install_db(monkeypatch, membership=False)
    assert repository.membership(user_id=USER_ID, tenant_id='tenant-a') is None
    with pytest.raises(PermissionError, match='not_found'):
        repository.require_permission(
            user_id=USER_ID, tenant_id='tenant-a', permission='credential.create'
        )


def test_totp_repository_lifecycle_is_transactional(monkeypatch):
    connection, cursor = install_db(monkeypatch)
    authenticator_id = repository.create_totp_authenticator(
        user_id=USER_ID, ciphertext='encrypted'
    )
    assert isinstance(authenticator_id, UUID)
    assert any('INSERT INTO api_identity_authenticators' in query for query, _ in cursor.calls)
    assert repository.pending_totp(user_id=USER_ID, authenticator_id=RECORD_ID) == 'ciphertext'
    assert repository.activate_totp_with_recovery_codes(
        user_id=USER_ID, authenticator_id=RECORD_ID, code_hashes=('hash-a', 'hash-b')
    )
    assert connection.committed is True
    assert sum('INSERT INTO api_identity_recovery_codes' in query for query, _ in cursor.calls) == 2

    failed_connection, _ = install_db(monkeypatch, activate_count=0)
    assert not repository.activate_totp_with_recovery_codes(
        user_id=USER_ID, authenticator_id=RECORD_ID, code_hashes=('unused',)
    )
    assert failed_connection.rolled_back is True


def test_invitation_credential_and_overview_never_return_secret_hashes(monkeypatch):
    _connection, cursor = install_db(monkeypatch)
    invitation_id = repository.create_invitation(
        organization_id=ORG_ID,
        actor_id=USER_ID,
        email='Invite@Example.Test',
        role='editor',
        token_hash='token-hash',
    )
    credential_id = repository.create_api_credential(
        organization_id=ORG_ID,
        actor_id=USER_ID,
        label='automation',
        prefix='b2_abcd',
        secret_hash='secret-hash',
        scopes=['content.read'],
    )
    assert isinstance(invitation_id, UUID)
    assert isinstance(credential_id, UUID)
    invitation_params = next(
        params for query, params in cursor.calls if 'INSERT INTO api_identity_invitations' in query
    )
    assert invitation_params[2] == 'invite@example.test'

    overview = repository.admin_overview(user_id=USER_ID, tenant_id='tenant-a')
    assert overview['organization']['id'] == str(ORG_ID)
    assert overview['members'][0]['role'] == 'owner'
    assert overview['credentials'][0]['prefix'] == 'b2_abcd'
    assert 'secret_hash' not in str(overview)


def test_role_update_preserves_last_owner_and_detects_stale_writes(monkeypatch):
    expected = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

    class RoleCursor(FakeCursor):
        def __init__(self, owner_count):
            super().__init__()
            self.owner_count = owner_count

        def fetchone(self):
            if 'SELECT role FROM api_identity_memberships' in self.query:
                return ('owner',)
            if 'SELECT role, updated_at' in self.query:
                return ('owner', expected)
            if 'SELECT COUNT(*)' in self.query:
                return (self.owner_count,)
            return super().fetchone()

    connections = []

    @contextmanager
    def last_owner_db(**_kwargs):
        connection = FakeConnection(RoleCursor(1))
        connections.append(connection)
        yield connection

    monkeypatch.setattr(repository, 'db_conn', last_owner_db)
    with pytest.raises(ValueError, match='last_owner'):
        repository.update_member_role(
            organization_id=ORG_ID,
            actor_id=USER_ID,
            member_id=USER_ID,
            new_role='admin',
            expected_updated_at=expected,
        )
    assert connections[-1].rolled_back is True
    assert not any('UPDATE api_identity_memberships SET role=' in q for q, _ in connections[-1]._cursor.calls)

    @contextmanager
    def two_owner_db(**_kwargs):
        connection = FakeConnection(RoleCursor(2))
        connections.append(connection)
        yield connection

    monkeypatch.setattr(repository, 'db_conn', two_owner_db)
    assert repository.update_member_role(
        organization_id=ORG_ID,
        actor_id=USER_ID,
        member_id=USER_ID,
        new_role='admin',
        expected_updated_at=expected,
    )
    assert connections[-1].committed is True


def test_invitation_acceptance_fails_closed_before_membership_on_mismatch(monkeypatch):
    connection, cursor = install_db(monkeypatch)
    assert repository.accept_invitation(
        token_hash='wrong',
        user_id=USER_ID,
        user_email='other@example.test',
        tenant_id='tenant-a',
    ) is None
    assert connection.rolled_back is True
    assert not any('INSERT INTO api_identity_memberships' in query for query, _ in cursor.calls)


def test_exact_revocation_and_atomic_recovery_login(monkeypatch):
    connection, cursor = install_db(monkeypatch)
    assert repository.revoke_invitation(
        organization_id=ORG_ID, invitation_id=RECORD_ID
    )
    assert repository.revoke_api_credential(
        organization_id=ORG_ID, credential_id=RECORD_ID
    )

    class RecoveryCursor(FakeCursor):
        def fetchone(self):
            if 'FROM api_identity_login_challenges' in self.query:
                return (RECORD_ID,)
            return super().fetchone()

    recovery_cursor = RecoveryCursor()
    recovery_connection = FakeConnection(recovery_cursor)

    @contextmanager
    def recovery_db(**_kwargs):
        yield recovery_connection

    monkeypatch.setattr(repository, 'db_conn', recovery_db)
    assert repository.consume_recovery_login(
        challenge_id=RECORD_ID, user_id=USER_ID, code_hash='hash-a'
    )
    assert recovery_connection.committed is True
    assert sum('SET used_at=NOW()' in query for query, _ in recovery_cursor.calls) == 1
    assert sum('SET consumed_at=NOW()' in query for query, _ in recovery_cursor.calls) == 1
