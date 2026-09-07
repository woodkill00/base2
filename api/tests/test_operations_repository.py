from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from api.repositories.operations import acknowledge, list_incidents, prune, summary


@contextmanager
def repository_connection(cursor):
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    yield connection


def test_summary_is_tenant_bound_and_normalizes_counts():
    cursor = MagicMock()
    cursor.fetchall.side_effect = [[('firing', 2)], [('passed', 8), ('failed', 1)]]
    cursor.fetchone.return_value = (11, 12)
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ) as connect:
        result = summary(tenant_id='tenant-one')
    connect.assert_called_once_with(tenant_id='tenant-one')
    assert result == {
        'services': {'enabled': 11, 'total': 12},
        'incidents': {'firing': 2},
        'synthetics24h': {'passed': 8, 'failed': 1},
    }
    assert all(call.args[1] == ('tenant-one',) for call in cursor.execute.call_args_list)


def test_incident_listing_bounds_limit_and_maps_safe_fields():
    now = datetime(2026, 9, 8, tzinfo=UTC)
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (UUID(int=1), 'high', 'firing', 'api.failed', 'owner-1', 3, now, now, None)
    ]
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ):
        result = list_incidents(tenant_id='tenant-one', limit=10000)
    assert result[0] == {
        'id': str(UUID(int=1)),
        'severity': 'high',
        'state': 'firing',
        'summaryCode': 'api.failed',
        'ownerRef': 'owner-1',
        'occurrenceCount': 3,
        'firstObservedAt': now,
        'lastObservedAt': now,
        'resolvedAt': None,
    }
    assert cursor.execute.call_args.args[1] == ('tenant-one', 100)


def test_acknowledgement_reports_changed_and_noop():
    incident_id = UUID(int=2)
    for returned, expected in ((('row',), True), (None, False)):
        cursor = MagicMock()
        cursor.fetchone.return_value = returned
        with patch(
            'api.repositories.operations.workspace_db_conn',
            return_value=repository_connection(cursor),
        ):
            assert (
                acknowledge(tenant_id='tenant-one', incident_id=incident_id, owner_ref='user-one')
                is expected
            )
        assert cursor.execute.call_args.args[1] == (
            'user-one',
            'tenant-one',
            str(incident_id),
        )


def test_retention_pruning_is_tenant_scoped_batched_and_policy_specific():
    cursor = MagicMock()
    cursor.rowcount = 4
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ):
        assert prune(tenant_id='tenant-one', batch_size=10000) == {
            'health': 4,
            'synthetics': 4,
            'incidents': 4,
        }
    assert [call.args[1] for call in cursor.execute.call_args_list] == [
        ('tenant-one', 30, 1000),
        ('tenant-one', 30, 1000),
        ('tenant-one', 365, 1000),
    ]
    assert "state='resolved'" not in cursor.execute.call_args_list[0].args[0]
    assert "state='resolved'" in cursor.execute.call_args_list[2].args[0]
