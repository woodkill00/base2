from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

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


def test_collection_and_dispatch_fan_out_only_configured_tenants(monkeypatch):
    monkeypatch.setattr(tasks.settings, 'OPERATIONS_ALERTS_ENABLED', True)
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one', 'tenant-two'])
    monkeypatch.setattr(tasks, 'fair_tenant_batch', lambda values: values)
    collect = MagicMock()
    dispatch = MagicMock()
    monkeypatch.setattr(tasks.collect_operations_site, 'delay', collect)
    monkeypatch.setattr(tasks.dispatch_operations_site_alerts, 'delay', dispatch)
    assert tasks.collect_operations_health.run() == 2
    assert tasks.dispatch_operations_alerts_task.run() == 2
    assert collect.call_args_list[0].args == ('tenant-one',)
    assert dispatch.call_args_list[1].args == ('tenant-two',)


def test_alert_dispatch_has_no_runtime_or_secret_reads_while_disabled(monkeypatch):
    monkeypatch.setattr(tasks.settings, 'OPERATIONS_ALERTS_ENABLED', False)
    configured = MagicMock()
    monkeypatch.setattr(tasks, 'configured_tenants', configured)
    assert tasks.dispatch_operations_alerts_task.run() == 0
    configured.assert_not_called()


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

    monkeypatch.setattr(tasks.collect_operations_site, 'run', MagicMock(return_value={'samples': 1}))
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
