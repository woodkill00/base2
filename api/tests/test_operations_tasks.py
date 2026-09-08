from unittest.mock import MagicMock

from api import tasks


def test_operations_beat_schedule_is_bounded_and_persistent():
    schedule = tasks.app.conf.beat_schedule
    assert schedule['operations-collect-health'] == {
        'task': 'app.collect_operations_health',
        'schedule': 60.0,
    }
    assert schedule['operations-dispatch-alerts']['schedule'] == 30.0
    assert schedule['operations-retention']['schedule'] == 86400.0


def test_collection_and_dispatch_fan_out_only_configured_tenants(monkeypatch):
    monkeypatch.setattr(tasks, 'configured_tenants', lambda: ['tenant-one', 'tenant-two'])
    collect = MagicMock()
    dispatch = MagicMock()
    monkeypatch.setattr(tasks.collect_operations_site, 'delay', collect)
    monkeypatch.setattr(tasks.dispatch_operations_site_alerts, 'delay', dispatch)
    assert tasks.collect_operations_health.run() == 2
    assert tasks.dispatch_operations_alerts_task.run() == 2
    assert collect.call_args_list[0].args == ('tenant-one',)
    assert dispatch.call_args_list[1].args == ('tenant-two',)


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
