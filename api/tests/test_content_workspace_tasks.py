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
        tasks.index_workspace_record_task(
            'site-a', '00000000-0000-0000-0000-000000000104', 3
        )
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
    for task in (tasks.publish_workspace_record, tasks.index_workspace_record_task):
        assert task.max_retries == 3
        assert task.autoretry_for == (Exception,)
        assert task.dont_autoretry_for == (ValueError,)
        assert task.retry_backoff is True
