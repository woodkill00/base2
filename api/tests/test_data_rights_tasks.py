from uuid import UUID

from api import tasks


def test_replay_scanner_is_bounded_and_dispatches_exact_ids(monkeypatch):
    ids = [
        UUID('00000000-0000-0000-0000-000000000901'),
        UUID('00000000-0000-0000-0000-000000000902'),
    ]
    captured = {}
    monkeypatch.setattr(
        tasks, 'queued_operation_ids',
        lambda **kwargs: captured.setdefault('limit', kwargs['limit']) or ids,
    )
    # The expression above returns the integer on first use; install a clearer
    # deterministic replacement after proving the bound was supplied.
    def queued(*, limit):
        captured['limit'] = limit
        return ids

    monkeypatch.setattr(tasks, 'queued_operation_ids', queued)
    dispatched = []
    monkeypatch.setattr(
        tasks.process_data_rights_operation, 'delay', lambda operation_id: dispatched.append(operation_id)
    )
    assert tasks.replay_data_rights_operations.run(limit=7) == 2
    assert captured['limit'] == 7
    assert dispatched == [str(item) for item in ids]


def test_beat_schedule_includes_replay_and_retention():
    schedule = tasks.app.conf.beat_schedule
    assert schedule['replay-data-rights-queue']['task'] == 'app.replay_data_rights_operations'
    assert schedule['expire-data-rights-results']['task'] == 'app.expire_data_rights_results'
