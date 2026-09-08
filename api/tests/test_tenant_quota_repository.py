from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from api.repositories.tenant_quota import QuotaRepositoryError, list_quotas, reserve, settle


@contextmanager
def connection(cursor):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    yield conn


def test_list_quotas_is_tenant_scoped_and_calculates_available():
    cursor = MagicMock()
    cursor.fetchall.return_value = [('jobs', 10, 3, 2, 7)]
    with patch('api.repositories.tenant_quota.workspace_db_conn', return_value=connection(cursor)):
        assert list_quotas(tenant_id='tenant-one') == [
            {
                'quotaKey': 'jobs',
                'limit': 10,
                'used': 3,
                'reserved': 2,
                'available': 5,
                'revision': 7,
            }
        ]
    assert cursor.execute.call_args.args[1] == ('tenant-one',)


def test_reserve_locks_quota_commits_and_exact_replay_is_a_noop():
    quota_id = UUID(int=1)
    cursor = MagicMock()
    cursor.fetchone.side_effect = [None, (quota_id, 10, 3, 2)]
    managed = connection(cursor)
    with patch('api.repositories.tenant_quota.workspace_db_conn', return_value=managed):
        result = reserve(
            tenant_id='tenant-one', quota_key='jobs', amount=4, reservation_id='job.reserve-001'
        )
    assert result == {'status': 'reserved', 'reservationId': 'job.reserve-001', 'replayed': False}
    assert cursor.execute.call_count == 5
    assert 'pg_advisory_xact_lock' in cursor.execute.call_args_list[0].args[0]
    assert 'FOR UPDATE' in cursor.execute.call_args_list[2].args[0]

    replay_cursor = MagicMock()
    replay_cursor.fetchone.return_value = (quota_id, 'jobs', 4, 'reserved')
    with patch(
        'api.repositories.tenant_quota.workspace_db_conn',
        return_value=connection(replay_cursor),
    ):
        assert reserve(
            tenant_id='tenant-one', quota_key='jobs', amount=4, reservation_id='job.reserve-001'
        )['replayed']
    assert replay_cursor.execute.call_count == 2


def test_reserve_exhaustion_and_changed_replay_fail_closed():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [None, (UUID(int=1), 10, 8, 2)]
    with (
        patch('api.repositories.tenant_quota.workspace_db_conn', return_value=connection(cursor)),
        pytest.raises(QuotaRepositoryError, match='exhausted'),
    ):
        reserve(
            tenant_id='tenant-one', quota_key='jobs', amount=1, reservation_id='job.reserve-002'
        )
    changed = MagicMock()
    changed.fetchone.return_value = (UUID(int=1), 'jobs', 4, 'reserved')
    with (
        patch('api.repositories.tenant_quota.workspace_db_conn', return_value=connection(changed)),
        pytest.raises(QuotaRepositoryError, match='conflict'),
    ):
        reserve(
            tenant_id='tenant-one', quota_key='jobs', amount=3, reservation_id='job.reserve-001'
        )


def test_settle_locks_and_atomically_moves_reserved_usage():
    cursor = MagicMock()
    cursor.fetchone.return_value = (UUID(int=1), 4, 'reserved')
    conn = MagicMock()

    @contextmanager
    def managed():
        conn.cursor.return_value.__enter__.return_value = cursor
        yield conn

    with patch('api.repositories.tenant_quota.workspace_db_conn', return_value=managed()):
        result = settle(tenant_id='tenant-one', reservation_id='job.reserve-001', commit=True)
    assert result['status'] == 'committed' and not result['replayed']
    assert 'used=used+%s' in cursor.execute.call_args_list[1].args[0]
    conn.commit.assert_called_once()
