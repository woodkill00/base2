from api import tasks


def test_workspace_index_replay_dispatches_only_discovered_fixed_arguments(monkeypatch):
    discovered = [('site-a', '00000000-0000-0000-0000-000000000104', 3)]
    delivered = []
    monkeypatch.setattr(tasks, 'due_index_records', lambda *, limit: discovered)
    monkeypatch.setattr(
        tasks.index_workspace_record_task,
        'delay',
        lambda site_id, record_id, version: delivered.append((site_id, record_id, version)),
    )

    assert tasks.replay_workspace_indexing(limit=25) == 1
    assert delivered == discovered


def test_workspace_index_task_calls_version_bound_worker(monkeypatch):
    called = []
    monkeypatch.setattr(
        tasks,
        'index_workspace_record',
        lambda **kwargs: called.append(kwargs) or 'indexed',
    )

    assert (
        tasks.index_workspace_record_task('site-a', '00000000-0000-0000-0000-000000000104', 3)
        == 'indexed'
    )
    assert called == [
        {
            'site_id': 'site-a',
            'record_id': tasks.UUID('00000000-0000-0000-0000-000000000104'),
            'job_version': 3,
        }
    ]


def test_workspace_mutation_tasks_have_bounded_dependency_retries():
    for task in (
        tasks.publish_workspace_record,
        tasks.index_workspace_record_task,
        tasks.scan_workspace_asset_task,
        tasks.process_workspace_export,
        tasks.validate_workspace_import,
        tasks.commit_workspace_import,
    ):
        assert task.max_retries == 3
        assert task.autoretry_for == (Exception,)
        assert task.dont_autoretry_for == (ValueError,)
        assert task.retry_backoff is True


def test_workspace_media_scan_replay_dispatches_only_discovered_ids(monkeypatch):
    discovered = [('site-a', '00000000-0000-0000-0000-000000007104')]
    delivered = []
    monkeypatch.setattr(tasks, 'due_media_scans', lambda *, limit: discovered)
    monkeypatch.setattr(
        tasks.scan_workspace_asset_task,
        'delay',
        lambda site_id, asset_id: delivered.append((site_id, asset_id)),
    )
    assert tasks.replay_workspace_media_scans(limit=10) == 1
    assert delivered == discovered


def test_workspace_media_scan_task_uses_private_store(monkeypatch):
    store = object()
    calls = []
    monkeypatch.setattr(tasks, '_workspace_artifact_store', lambda: store)
    monkeypatch.setattr(
        tasks,
        'scan_workspace_asset',
        lambda **kwargs: calls.append(kwargs) or 'scanned_clean',
    )
    asset_id = '00000000-0000-0000-0000-000000007104'
    assert tasks.scan_workspace_asset_task('site-a', asset_id) == 'scanned_clean'
    assert calls == [
        {'site_id': 'site-a', 'asset_id': tasks.UUID(asset_id), 'artifact_store': store}
    ]


def test_workspace_export_replay_and_task_use_only_discovered_fixed_ids(monkeypatch):
    discovered = [('site-a', '00000000-0000-0000-0000-000000006104')]
    delivered = []
    monkeypatch.setattr(tasks, 'due_export_jobs', lambda *, limit: discovered)
    monkeypatch.setattr(
        tasks.process_workspace_export,
        'delay',
        lambda site_id, job_id: delivered.append((site_id, job_id)),
    )
    assert tasks.replay_workspace_exports(limit=10) == 1
    assert delivered == discovered

    store = object()
    calls = []
    monkeypatch.setattr(tasks, '_workspace_artifact_store', lambda: store)
    monkeypatch.setattr(
        tasks, 'process_export_job', lambda **kwargs: calls.append(kwargs) or 'completed'
    )
    assert tasks.process_workspace_export(*discovered[0]) == 'completed'
    assert calls == [
        {
            'site_id': 'site-a',
            'job_id': tasks.UUID(discovered[0][1]),
            'artifact_store': store,
        }
    ]


def test_export_task_terminal_failure_hook_redacts_and_records(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks, 'mark_export_failed', lambda **kwargs: calls.append(kwargs))
    task = tasks.WorkspaceExportTask()
    task.on_failure(
        RuntimeError('provider password=private'),
        'task-id',
        ('site-a', '00000000-0000-0000-0000-000000006104'),
        {},
        None,
    )
    assert calls == [
        {
            'site_id': 'site-a',
            'job_id': tasks.UUID('00000000-0000-0000-0000-000000006104'),
            'error_code': '',
        }
    ]


def test_expire_export_task_calls_bounded_worker(monkeypatch):
    monkeypatch.setattr(tasks, 'expire_workspace_export_jobs', lambda *, limit: limit)
    assert tasks.expire_workspace_exports(limit=100) == 100


def test_import_validation_replay_and_task_use_only_discovered_fixed_ids(monkeypatch):
    discovered = [('site-a', '00000000-0000-0000-0000-000000005104')]
    delivered = []
    monkeypatch.setattr(tasks, 'due_import_validations', lambda *, limit: discovered)
    monkeypatch.setattr(
        tasks.validate_workspace_import,
        'delay',
        lambda site_id, job_id: delivered.append((site_id, job_id)),
    )
    assert tasks.replay_workspace_import_validations(limit=10) == 1
    assert delivered == discovered

    store = object()
    calls = []
    monkeypatch.setattr(tasks, '_workspace_artifact_store', lambda: store)
    monkeypatch.setattr(
        tasks, 'validate_import_job', lambda **kwargs: calls.append(kwargs) or 'validated'
    )
    assert tasks.validate_workspace_import(*discovered[0]) == 'validated'
    assert calls == [
        {
            'site_id': 'site-a',
            'job_id': tasks.UUID(discovered[0][1]),
            'artifact_store': store,
        }
    ]


def test_import_commit_replay_and_task_use_only_discovered_fixed_ids(monkeypatch):
    discovered = [('site-a', '00000000-0000-0000-0000-000000005104')]
    delivered = []
    monkeypatch.setattr(tasks, 'due_import_commits', lambda *, limit: discovered)
    monkeypatch.setattr(
        tasks.commit_workspace_import,
        'delay',
        lambda site_id, job_id: delivered.append((site_id, job_id)),
    )
    assert tasks.replay_workspace_import_commits(limit=10) == 1
    assert delivered == discovered

    store = object()
    calls = []
    monkeypatch.setattr(tasks, '_workspace_artifact_store', lambda: store)
    monkeypatch.setattr(
        tasks, 'process_import_commit', lambda **kwargs: calls.append(kwargs) or 'completed'
    )
    assert tasks.commit_workspace_import(*discovered[0]) == 'completed'
    assert calls == [
        {
            'site_id': 'site-a',
            'job_id': tasks.UUID(discovered[0][1]),
            'artifact_store': store,
        }
    ]


def test_import_task_terminal_failure_hook_redacts_and_records(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks, 'mark_import_failed', lambda **kwargs: calls.append(kwargs))
    task = tasks.WorkspaceImportTask()
    task.on_failure(
        RuntimeError('provider password=private'),
        'task-id',
        ('site-a', '00000000-0000-0000-0000-000000005104'),
        {},
        None,
    )
    assert calls == [
        {
            'site_id': 'site-a',
            'job_id': tasks.UUID('00000000-0000-0000-0000-000000005104'),
            'error_code': '',
        }
    ]


def test_import_tasks_use_terminal_failure_hook():
    assert isinstance(tasks.validate_workspace_import, tasks.WorkspaceImportTask)
    assert isinstance(tasks.commit_workspace_import, tasks.WorkspaceImportTask)
