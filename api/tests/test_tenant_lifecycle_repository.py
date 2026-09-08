from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from api.repositories.tenant_lifecycle import (
    TenantLifecycleRepositoryError,
    apply_operation,
    apply_transition,
    consume_destructive_approval_nonce,
    get_state,
    provision,
)


class Connection:
    def __init__(self, cursor):
        self.cursor_value = cursor
        self.commit = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_value


def test_destructive_approval_nonce_is_durably_consumed_once():
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.__enter__.return_value = cursor
    now = datetime(2026, 9, 8, tzinfo=UTC)
    connection = Connection(cursor)
    with patch(
        'api.repositories.tenant_lifecycle.workspace_db_conn',
        return_value=connection,
    ):
        assert consume_destructive_approval_nonce(
            'tenant-one', 'delete-start-0001', 'a' * 64, now + timedelta(minutes=10)
        )
    assert 'ON CONFLICT (site_id,nonce) DO NOTHING' in cursor.execute.call_args.args[0]
    connection.commit.assert_called_once()

    cursor.rowcount = 0
    with patch(
        'api.repositories.tenant_lifecycle.workspace_db_conn',
        return_value=Connection(cursor),
    ):
        assert not consume_destructive_approval_nonce(
            'tenant-one', 'delete-start-0001', 'a' * 64, now + timedelta(minutes=10)
        )


def test_destructive_approval_nonce_rejects_invalid_input_without_database_access():
    with patch('api.repositories.tenant_lifecycle.workspace_db_conn') as connect:
        assert not consume_destructive_approval_nonce(
            'tenant-one', 'short', 'a' * 64, datetime.now()
        )
    connect.assert_not_called()


def test_destructive_transition_consumes_nonce_and_updates_state_in_one_transaction():
    operation_id = UUID('00000000-0000-4000-8000-000000000106')
    current = ('archived', 'owner-one', {}, 4, operation_id, 'a' * 64)
    updated = ('deleting', 'owner-one', {}, 5, operation_id, 'b' * 64)
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.side_effect = [current, None, updated]
    cursor.rowcount = 1
    connection = Connection(cursor)
    with patch('api.repositories.tenant_lifecycle.workspace_db_conn', return_value=connection):
        result = apply_transition(
            tenant_id='tenant-one',
            current='archived',
            target='deleting',
            owner_ref='owner-one',
            expected_revision=4,
            operation_id=operation_id,
            approval={
                'nonce': 'delete-atomic-0001',
                'digest': 'c' * 64,
                'expiresAt': datetime(2026, 9, 8, 0, 10, tzinfo=UTC),
            },
        )
    assert result['state'] == 'deleting'
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    nonce_index = next(i for i, sql in enumerate(statements) if 'destructiveapprovaluse' in sql)
    state_index = next(
        i for i, sql in enumerate(statements) if 'UPDATE sitecontent_tenantlifecyclestate' in sql
    )
    assert nonce_index < state_index
    connection.commit.assert_called_once()


def test_get_state_serializes_the_tenant_private_record():
    operation_id = UUID('00000000-0000-4000-8000-000000000106')
    cursor = MagicMock()
    cursor.fetchone.return_value = ('active', 'owner-one', {'locale': 'en'}, 4, operation_id, 'a' * 64)
    cursor.__enter__.return_value = cursor
    with patch(
        'api.repositories.tenant_lifecycle.workspace_db_conn',
        return_value=Connection(cursor),
    ):
        result = get_state(tenant_id='tenant-one')
    assert result == {
        'tenantId': 'tenant-one',
        'state': 'active',
        'owner': 'owner-one',
        'configuration': {'locale': 'en'},
        'revision': 4,
        'operationId': str(operation_id),
        'receiptDigest': 'a' * 64,
        'idempotent': False,
    }


def test_get_state_rejects_a_missing_lifecycle_record():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    cursor.__enter__.return_value = cursor
    with (
        patch(
            'api.repositories.tenant_lifecycle.workspace_db_conn',
            return_value=Connection(cursor),
        ),
        pytest.raises(TenantLifecycleRepositoryError, match='lifecycle_missing'),
    ):
        get_state(tenant_id='tenant-one')


def test_provision_creates_state_and_event_in_one_transaction():
    operation_id = UUID('00000000-0000-4000-8000-000000000106')
    row = ('provisioning', 'owner-one', {'locale': 'en'}, 1, operation_id, 'b' * 64)
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    cursor.__enter__.return_value = cursor

    def execute(statement, _arguments):
        cursor.rowcount = 1 if 'INSERT INTO sitecontent_tenantlifecyclestate' in statement else 0

    cursor.execute.side_effect = execute
    connection = Connection(cursor)
    with patch(
        'api.repositories.tenant_lifecycle.workspace_db_conn', return_value=connection
    ):
        result = provision(
            tenant_id='tenant-one',
            owner_ref='owner-one',
            operation_id=operation_id,
            configuration={'locale': 'en'},
        )
    assert result['state'] == 'provisioning'
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert any('INSERT INTO sitecontent_tenantlifecycleevent' in sql for sql in statements)
    connection.commit.assert_called_once()


def test_provision_exact_replay_is_idempotent_and_changed_replay_conflicts():
    operation_id = UUID('00000000-0000-4000-8000-000000000106')
    configuration = {'locale': 'en'}
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.rowcount = 0
    connection = Connection(cursor)
    with (
        patch(
            'api.repositories.tenant_lifecycle.workspace_db_conn', return_value=connection
        ),
        patch('api.repositories.tenant_lifecycle._digest', return_value='b' * 64),
    ):
        cursor.fetchone.return_value = (
            'provisioning',
            'owner-one',
            configuration,
            1,
            operation_id,
            'b' * 64,
        )
        assert provision(
            tenant_id='tenant-one',
            owner_ref='owner-one',
            operation_id=operation_id,
            configuration=configuration,
        )['idempotent']
        cursor.fetchone.return_value = (
            'provisioning',
            'owner-one',
            configuration,
            1,
            operation_id,
            'c' * 64,
        )
        with pytest.raises(TenantLifecycleRepositoryError, match='lifecycle_exists'):
            provision(
                tenant_id='tenant-one',
                owner_ref='owner-one',
                operation_id=operation_id,
                configuration=configuration,
            )


def test_apply_operation_configures_and_transfers_with_revision_control():
    operation_id = UUID('00000000-0000-4000-8000-000000000106')
    prior = ('active', 'owner-one', {'locale': 'en'}, 3, operation_id, 'a' * 64)
    updated = ('active', 'owner-one', {'locale': 'ar'}, 4, operation_id, 'b' * 64)
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.side_effect = [prior, None, updated]

    def execute(statement, _arguments):
        if 'UPDATE sitecontent_tenantlifecyclestate' in statement:
            cursor.rowcount = 1

    cursor.execute.side_effect = execute
    connection = Connection(cursor)
    with patch(
        'api.repositories.tenant_lifecycle.workspace_db_conn', return_value=connection
    ):
        result = apply_operation(
            tenant_id='tenant-one',
            operation='configure',
            owner_ref='owner-one',
            target_owner_ref='',
            configuration={'locale': 'ar'},
            expected_revision=3,
            operation_id=operation_id,
        )
    assert result['configuration'] == {'locale': 'ar'}
    assert result['revision'] == 4
    connection.commit.assert_called_once()


def test_apply_operation_exact_replay_and_conflicts_fail_closed():
    operation_id = UUID('00000000-0000-4000-8000-000000000106')
    prior = ('active', 'owner-one', {}, 3, operation_id, 'a' * 64)
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.side_effect = [prior, ('export', 'owner-one', '', 4)]
    connection = Connection(cursor)
    with patch(
        'api.repositories.tenant_lifecycle.workspace_db_conn', return_value=connection
    ):
        assert apply_operation(
            tenant_id='tenant-one',
            operation='export',
            owner_ref='owner-one',
            target_owner_ref='',
            configuration=None,
            expected_revision=3,
            operation_id=operation_id,
        )['idempotent']

    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.side_effect = [prior, ('transfer', 'owner-one', 'owner-two', 4)]
    with (
        patch(
            'api.repositories.tenant_lifecycle.workspace_db_conn',
            return_value=Connection(cursor),
        ),
        pytest.raises(TenantLifecycleRepositoryError, match='operation_conflict'),
    ):
        apply_operation(
            tenant_id='tenant-one',
            operation='export',
            owner_ref='owner-one',
            target_owner_ref='',
            configuration=None,
            expected_revision=3,
            operation_id=operation_id,
        )

    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.side_effect = [prior, None]
    with (
        patch(
            'api.repositories.tenant_lifecycle.workspace_db_conn',
            return_value=Connection(cursor),
        ),
        pytest.raises(TenantLifecycleRepositoryError, match='revision_conflict'),
    ):
        apply_operation(
            tenant_id='tenant-one',
            operation='export',
            owner_ref='wrong-owner',
            target_owner_ref='',
            configuration=None,
            expected_revision=3,
            operation_id=operation_id,
        )
