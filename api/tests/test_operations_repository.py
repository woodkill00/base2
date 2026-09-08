from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

from api.repositories.operations import (
    acknowledge,
    due_alert_deliveries,
    incident_detail,
    list_incidents,
    overview,
    prune,
    record_probe_batch,
    summary,
    update_alert_delivery,
)


@contextmanager
def repository_connection(cursor):
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    cursor.connection = connection
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
        (UUID(int=1), 'production', 'high', 'firing', 'api.failed', 'owner-1', 3, now, now, None)
    ]
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ):
        result = list_incidents(tenant_id='tenant-one', limit=10000)
    assert result[0] == {
        'id': str(UUID(int=1)),
        'environment': 'production',
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
        cursor.connection.commit.assert_called_once()
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
    cursor.connection.commit.assert_called_once()
    assert [call.args[1] for call in cursor.execute.call_args_list] == [
        ('tenant-one', 30, 1000),
        ('tenant-one', 30, 1000),
        ('tenant-one', 365, 1000),
    ]
    assert "state='resolved'" not in cursor.execute.call_args_list[0].args[0]
    assert "state='resolved'" in cursor.execute.call_args_list[2].args[0]
    assert 'resolved_at <' in cursor.execute.call_args_list[2].args[0]
    assert 'ORDER BY resolved_at' in cursor.execute.call_args_list[2].args[0]


def test_overview_exposes_bounded_service_release_objective_and_evidence_views():
    now = datetime(2026, 9, 8, tzinfo=UTC)
    cursor = MagicMock()
    cursor.fetchall.side_effect = [
        [
            (
                UUID(int=3),
                'api.health',
                'staging',
                True,
                'release-one',
                'healthy',
                'api.ready',
                4,
                now,
                now,
            )
        ],
        [('api.availability', 'request.success', 0.999, 0.995, 1440)],
        [(UUID(int=4), 'member.login', 'member', 'a' * 40, 'passed', 'b' * 64, now, now)],
    ]
    cursor.fetchone.side_effect = [(2, 1, 3), (4, 1), (5, 2)]
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ):
        result = overview(tenant_id='tenant-one')
    assert result['site'] == {'id': 'tenant-one', 'serviceCount': 1, 'releaseCount': 1}
    assert result['services'][0]['health']['state'] == 'healthy'
    assert result['objectives'][0]['target'] == 0.999
    assert result['synthetics'][0]['sourceCommit'] == 'a' * 40
    assert result['runtime'] == {
        'jobs': {'ready': 2, 'leased': 1, 'deadLetters': 3},
        'schedules': {'enabled': 4, 'late': 1},
        'alerts': {'pending': 5, 'terminal': 2},
    }
    assert [call.args[1] for call in cursor.execute.call_args_list] == [
        ('tenant-one', 'tenant-one'),
        ('tenant-one',),
        ('tenant-one',),
        ('tenant-one',),
        ('tenant-one',),
        ('tenant-one',),
    ]


def test_incident_detail_is_tenant_bound_and_includes_timeline():
    now = datetime(2026, 9, 8, tzinfo=UTC)
    incident_id = UUID(int=5)
    cursor = MagicMock()
    cursor.fetchone.return_value = (
        incident_id,
        'production',
        'high',
        'firing',
        'api.failed',
        'owner-one',
        2,
        now,
        now,
        None,
    )
    cursor.fetchall.return_value = [(UUID(int=6), 'incident.opened', 'system', {}, now)]
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ):
        result = incident_detail(tenant_id='tenant-one', incident_id=incident_id)
    assert result and result['timeline'][0]['eventKey'] == 'incident.opened'
    assert [call.args[1] for call in cursor.execute.call_args_list] == [
        ('tenant-one', str(incident_id)),
        ('tenant-one', str(incident_id)),
    ]


def test_failing_probe_is_persisted_and_opens_one_durable_alert():
    now = datetime(2026, 9, 8, tzinfo=UTC)
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(UUID(int=10),), None]
    cursor.rowcount = 1
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ):
        result = record_probe_batch(
            tenant_id='tenant-one',
            environment='staging',
            now=now,
            results=[
                {
                    'probeId': 'api.health',
                    'state': 'unavailable',
                    'code': 'api.unavailable',
                    'latencyMs': 4,
                    'observedAt': now.isoformat(),
                    'expiresAt': (now.replace(minute=1)).isoformat(),
                }
            ],
        )
    assert result == {'samples': 1, 'opened': 1, 'resolved': 0, 'alerts': 1}
    cursor.connection.commit.assert_called_once()
    statements = '\n'.join(call.args[0] for call in cursor.execute.call_args_list)
    assert 'sitecontent_operationshealthsample' in statements
    assert 'sitecontent_operationsincident' in statements
    assert 'sitecontent_operationsalertdelivery' in statements


def test_due_alerts_and_optimistic_delivery_update_are_tenant_bounded():
    now = datetime(2026, 9, 8, tzinfo=UTC)
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (UUID(int=11), 1, 5, now, 'a' * 64, 'high', 'api.unavailable', UUID(int=12))
    ]
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ):
        due = due_alert_deliveries(tenant_id='tenant-one', now=now, limit=999)
    assert due[0]['incidentFingerprint'] == 'a' * 64
    assert cursor.execute.call_args.args[1][:4] == ('tenant-one', now, now, 50)
    assert cursor.execute.call_args.args[1][5] == now + timedelta(minutes=2)

    cursor = MagicMock()
    cursor.fetchone.return_value = (UUID(int=11),)
    with patch(
        'api.repositories.operations.workspace_db_conn',
        return_value=repository_connection(cursor),
    ):
        changed = update_alert_delivery(
            tenant_id='tenant-one',
            delivery_id=UUID(int=11),
            claim_token=UUID(int=12),
            status='sent',
            next_attempt_at=None,
            receipt_digest='b' * 64,
        )
    assert changed
    assert cursor.execute.call_args.args[1][-3:] == (
        'tenant-one', str(UUID(int=11)), str(UUID(int=12))
    )
    cursor.connection.commit.assert_called_once()
