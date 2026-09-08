from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from api import tasks


def test_operations_beat_schedule_is_bounded_and_persistent():
    schedule = tasks.app.conf.beat_schedule
    assert schedule['operations-collect-health'] == {
        'task': 'app.collect_operations_health',
        'schedule': 60.0,
    }
    assert schedule['operations-dispatch-alerts']['schedule'] == 30.0
    assert schedule['operations-retention']['schedule'] == 86400.0
    assert schedule['runtime-materialize-schedules']['schedule'] == 30.0
    assert schedule['runtime-claim-jobs']['schedule'] == 15.0
    assert schedule['email-replay-outbox']['schedule'] == 60.0


def test_workers_are_partitioned_by_fixed_task_routes():
    routes = tasks.app.conf.task_routes
    assert routes['app.send_email_outbox'] == {'queue': 'email'}
    assert routes['app.replay_email_outbox'] == {'queue': 'email'}
    assert routes['app.process_data_rights_operation'] == {'queue': 'data-rights'}
    assert routes['app.replay_data_rights_operations'] == {'queue': 'data-rights'}
    assert routes['app.expire_data_rights_results'] == {'queue': 'data-rights'}
    assert routes['app.process_workspace_export'] == {'queue': 'content'}
    assert tasks.app.conf.task_default_queue == 'runtime'
    registered = {name for name in tasks.app.tasks if name.startswith('app.')}
    assert set(routes) == registered
    tasks._validate_closed_task_routing()


def test_worker_heartbeat_is_role_specific_and_unknown_roles_emit_nothing(monkeypatch):
    heartbeat = MagicMock()
    monkeypatch.setattr(tasks, 'mark_runtime_heartbeat', heartbeat)
    monkeypatch.setattr(tasks.settings, 'BASE2_PROCESS_ROLE', 'content-worker')
    tasks._observe_worker()
    heartbeat.assert_called_once_with('workers:content-worker')
    heartbeat.reset_mock()
    monkeypatch.setattr(tasks.settings, 'BASE2_PROCESS_ROLE', 'api')
    tasks._observe_worker()
    heartbeat.assert_not_called()


def test_task_signals_validate_routes_stamp_time_and_observe_queue_delay(monkeypatch):
    routes = dict(tasks.app.conf.task_routes)
    routes.pop('app.ping')
    monkeypatch.setattr(tasks.app.conf, 'task_routes', routes)
    with pytest.raises(RuntimeError, match='task_routes_unclassified:app.ping'):
        tasks._validate_closed_task_routing()

    headers = {}
    tasks._stamp_published_at(headers=headers)
    assert datetime.fromisoformat(headers['base2PublishedAt']).tzinfo is not None
    tasks._stamp_published_at(headers='not-a-dictionary')

    observation = MagicMock()
    monkeypatch.setattr(tasks, 'mark_queue_observation', observation)
    task = MagicMock()
    task.request.headers = {'base2PublishedAt': datetime.now(UTC).isoformat()}
    tasks._observe_queue_delay(task=task)
    assert observation.call_args.kwargs['published_at'].tzinfo is not None
    observation.reset_mock()
    task.request.headers = {'base2PublishedAt': 'invalid'}
    tasks._observe_queue_delay(task=task)
    observation.assert_not_called()


def test_production_lifecycle_and_dispatch_admission_fail_closed(monkeypatch):
    from api.repositories import tenant_lifecycle

    monkeypatch.setattr(tasks.settings, 'ENV', 'production')
    monkeypatch.setattr(tenant_lifecycle, 'get_state', lambda **_kwargs: {'state': 'active'})
    assert tasks._tenant_serving('tenant-one') is True
    monkeypatch.setattr(
        tenant_lifecycle,
        'get_state',
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError('database unavailable')),
    )
    assert tasks._tenant_serving('tenant-one') is False

    client = MagicMock()
    client.set.side_effect = [True, False]
    monkeypatch.setattr(tasks, 'redis_client', lambda: client)
    token = tasks._reserve_tenant_dispatch('collect', 'tenant-one')
    assert token is not None
    assert tasks._reserve_tenant_dispatch('collect', 'tenant-one') is None
    tasks._release_tenant_dispatch('collect', 'tenant-one', token)
    client.eval.assert_called_once()
    client.eval.reset_mock()
    client.eval.side_effect = None
    client.eval.return_value = 1
    assert tasks._reserve_runtime_fanout(reserve=16) is True
    assert tasks._reserve_runtime_fanout(reserve=17) is False
    client.eval.side_effect = RuntimeError('redis unavailable')
    assert tasks._reserve_runtime_fanout(reserve=16) is False


def test_collection_fanout_releases_dispatch_reservation_when_enqueue_fails(monkeypatch):
    monkeypatch.setattr(tasks, '_reserve_runtime_fanout', lambda **_kwargs: True)
    monkeypatch.setattr(tasks, '_release_runtime_fanout', MagicMock())
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one'])
    monkeypatch.setattr(tasks, 'fair_tenant_batch', lambda values, **_kwargs: values)
    monkeypatch.setattr(tasks, '_tenant_serving', lambda _tenant: True)
    monkeypatch.setattr(tasks, '_reserve_tenant_dispatch', lambda *_args: 'token-one')
    release = MagicMock()
    monkeypatch.setattr(tasks, '_release_tenant_dispatch', release)
    monkeypatch.setattr(
        tasks.collect_operations_site,
        'delay',
        MagicMock(side_effect=RuntimeError('broker unavailable')),
    )
    with pytest.raises(RuntimeError, match='broker unavailable'):
        tasks.collect_operations_health.run()
    release.assert_called_once_with('collect', 'tenant-one', 'token-one')


def test_collection_and_dispatch_fan_out_only_configured_tenants(monkeypatch):
    monkeypatch.setattr(tasks, '_reserve_runtime_fanout', lambda **_kwargs: True)
    monkeypatch.setattr(tasks, '_release_runtime_fanout', MagicMock())
    monkeypatch.setattr(tasks.settings, 'OPERATIONS_ALERTS_ENABLED', True)
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one', 'tenant-two'])
    monkeypatch.setattr(tasks, 'fair_tenant_batch', lambda values, **_kwargs: values)
    monkeypatch.setattr(tasks, '_reserve_tenant_dispatch', lambda kind, site: f'{kind}-{site}')
    collect = MagicMock()
    dispatch = MagicMock()
    monkeypatch.setattr(tasks.collect_operations_site, 'delay', collect)
    monkeypatch.setattr(tasks.dispatch_operations_site_alerts, 'delay', dispatch)
    assert tasks.collect_operations_health.run() == 2
    assert tasks.dispatch_operations_alerts_task.run() == 2
    assert collect.call_args_list[0].args == ('tenant-one', 'collect-tenant-one')
    assert dispatch.call_args_list[1].args == ('tenant-two', 'alerts-tenant-two')


def test_production_fanout_and_site_work_fail_closed_for_nonactive_tenants(monkeypatch):
    monkeypatch.setattr(tasks.settings, 'ENV', 'production')
    monkeypatch.setattr(tasks, '_reserve_runtime_fanout', lambda **_kwargs: True)
    monkeypatch.setattr(tasks, '_release_runtime_fanout', MagicMock())
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one'])
    monkeypatch.setattr(tasks, 'fair_tenant_batch', lambda values, **_kwargs: values)
    monkeypatch.setattr(tasks, '_tenant_serving', lambda _tenant: False)
    delayed = MagicMock()
    monkeypatch.setattr(tasks.collect_operations_site, 'delay', delayed)
    assert tasks.collect_operations_health.run() == 0
    delayed.assert_not_called()
    try:
        tasks.collect_operations_site.run('tenant-one')
    except ValueError as exc:
        assert str(exc) == 'tenant_not_serving'
    else:
        raise AssertionError('nonactive production tenant was served')


def test_operations_fanout_skips_already_reserved_tenant(monkeypatch):
    monkeypatch.setattr(tasks, '_reserve_runtime_fanout', lambda **_kwargs: True)
    monkeypatch.setattr(tasks, '_release_runtime_fanout', MagicMock())
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one', 'tenant-two'])
    monkeypatch.setattr(tasks, 'fair_tenant_batch', lambda values, **_kwargs: values)
    monkeypatch.setattr(
        tasks,
        '_reserve_tenant_dispatch',
        lambda kind, site: None if site == 'tenant-one' else 'dispatch-token',
    )
    delayed = MagicMock()
    monkeypatch.setattr(tasks.collect_operations_site, 'delay', delayed)
    assert tasks.collect_operations_health.run() == 1
    delayed.assert_called_once_with('tenant-two', 'dispatch-token')


def test_email_replay_fans_out_only_durable_due_rows(monkeypatch):
    first, second = UUID(int=10), UUID(int=11)
    monkeypatch.setattr(tasks, 'replayable_outbox_ids', lambda limit: [first, second])
    delayed = MagicMock()
    monkeypatch.setattr(tasks.send_email_outbox, 'delay', delayed)
    assert tasks.replay_email_outbox.run(limit=2) == 2
    assert delayed.call_args_list[0].args == (str(first),)
    assert delayed.call_args_list[1].args == (str(second),)


def test_alert_dispatch_has_no_runtime_or_secret_reads_while_disabled(monkeypatch):
    monkeypatch.setattr(tasks.settings, 'OPERATIONS_ALERTS_ENABLED', False)
    configured = MagicMock()
    monkeypatch.setattr(tasks, 'configured_tenants', configured)
    assert tasks.dispatch_operations_alerts_task.run() == 0
    configured.assert_not_called()


def test_operations_fanout_fails_closed_before_queue_saturation(monkeypatch):
    monkeypatch.setattr(tasks, '_reserve_runtime_fanout', lambda **_kwargs: False)
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one'])
    fair = MagicMock()
    monkeypatch.setattr(tasks, 'fair_tenant_batch', fair)
    assert tasks.collect_operations_health.run() == 0
    fair.assert_not_called()


def test_runtime_fanout_reservation_is_atomic_across_concurrent_ticks(monkeypatch):
    class AtomicRedis:
        depth = 70
        held = 0

        def eval(self, script, _keys, *_args):
            if 'llen' in script:
                reserve, ceiling, _ttl = map(int, _args[2:])
                if self.depth + self.held + reserve > ceiling:
                    return 0
                self.held += reserve
                return 1
            released = int(_args[1])
            prior = self.held
            self.held = max(0, self.held - released)
            return min(prior, released)

    client = AtomicRedis()
    monkeypatch.setattr(tasks, 'redis_client', lambda: client)
    assert tasks._reserve_runtime_fanout(reserve=16) is True
    assert tasks._reserve_runtime_fanout(reserve=16) is False
    tasks._release_runtime_fanout(count=16)
    assert client.held == 0
    assert tasks._reserve_runtime_fanout(reserve=16) is True


def test_fanout_releases_every_capacity_slot_after_enqueue(monkeypatch):
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one', 'tenant-two'])
    monkeypatch.setattr(tasks, 'fair_tenant_batch', lambda values, **_kwargs: values)
    monkeypatch.setattr(tasks, '_reserve_runtime_fanout', lambda **_kwargs: True)
    release_capacity = MagicMock()
    monkeypatch.setattr(tasks, '_release_runtime_fanout', release_capacity)
    monkeypatch.setattr(tasks, '_tenant_serving', lambda tenant: tenant == 'tenant-one')
    monkeypatch.setattr(tasks, '_reserve_tenant_dispatch', lambda *_args: 'token')
    monkeypatch.setattr(tasks.collect_operations_site, 'delay', MagicMock())
    assert tasks.collect_operations_health.run() == 1
    assert release_capacity.call_count == 2


def test_schedule_materialization_is_allowlisted_idempotent_and_always_settled(monkeypatch):
    due = datetime(2026, 9, 8, tzinfo=UTC)
    schedule = {
        'scheduleId': str(UUID(int=1)),
        'scheduleKey': 'operations.collect',
        'jobType': 'operations.collect',
        'nextRunAt': due.isoformat(),
        'scheduledFor': due.isoformat(),
        'revision': 2,
        'claimToken': str(UUID(int=2)),
    }
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one'])
    monkeypatch.setattr(tasks, 'claim_due_schedules', lambda **kwargs: [schedule])
    enqueue = MagicMock()
    settle = MagicMock()
    heartbeat = MagicMock()
    monkeypatch.setattr(tasks, 'enqueue_job', enqueue)
    monkeypatch.setattr(tasks, 'settle_schedule_claim', settle)
    monkeypatch.setattr(tasks, 'mark_runtime_heartbeat', heartbeat)
    assert tasks.materialize_runtime_schedules.run() == 1
    assert enqueue.call_args.kwargs['idempotency_key'].endswith(due.isoformat())
    assert settle.call_args.kwargs['succeeded'] is True
    heartbeat.assert_called_once()

    schedule['jobType'] = 'arbitrary.command'
    try:
        tasks.materialize_runtime_schedules.run()
    except ValueError as exc:
        assert str(exc) == 'schedule:job_type_not_allowed'
    else:
        raise AssertionError('unsafe schedule unexpectedly accepted')
    assert settle.call_args.kwargs['succeeded'] is False


def test_runtime_job_claim_and_settlement_are_lease_bound(monkeypatch):
    job = {
        'jobId': str(UUID(int=3)),
        'jobType': 'operations.collect',
        'leaseToken': str(UUID(int=4)),
        'generation': 3,
    }
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one'])
    monkeypatch.setattr(tasks, 'claim_jobs', lambda **kwargs: [job])
    delayed = MagicMock()
    monkeypatch.setattr(tasks.run_runtime_job, 'delay', delayed)
    assert tasks.claim_runtime_jobs_task.run() == 1
    delayed.assert_called_once_with('tenant-one', job)

    monkeypatch.setattr(
        tasks.collect_operations_site, 'run', MagicMock(return_value={'samples': 1})
    )
    settle = MagicMock(return_value='succeeded')
    monkeypatch.setattr(tasks, 'settle_job', settle)
    monkeypatch.setattr(tasks, 'renew_job_lease', MagicMock())
    assert tasks.run_runtime_job.run('tenant-one', job) == 'succeeded'
    assert settle.call_args.kwargs['lease_token'] == UUID(int=4)
    assert settle.call_args.kwargs['generation'] == 3


def test_site_collection_maps_nonlive_environment_to_preview(monkeypatch):
    collect = MagicMock(return_value={'samples': 16})
    monkeypatch.setattr(tasks, 'collect_site', collect)
    monkeypatch.setattr(tasks.settings, 'ENV', 'development')
    assert tasks.collect_operations_site.run('tenant-one') == {'samples': 16}
    assert collect.call_args.kwargs == {'tenant_id': 'tenant-one', 'environment': 'preview'}


def test_retention_runs_per_explicit_tenant(monkeypatch):
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one'])
    prune = MagicMock(return_value={'health': 2})
    monkeypatch.setattr(tasks, 'prune_operations', prune)
    assert tasks.prune_operations_evidence.run() == {'tenant-one': {'health': 2}}
    prune.assert_called_once_with(tenant_id='tenant-one')
