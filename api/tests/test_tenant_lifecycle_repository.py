from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from api.repositories.tenant_lifecycle import consume_destructive_approval_nonce


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
