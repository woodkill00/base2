"""Deterministic local adapter units; PostgreSQL guarantees live in the integration suite."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from api.services import workspace_review_notifications as worker

NOW = datetime(2026, 10, 31, 10, tzinfo=UTC)


class Cursor:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((' '.join(sql.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        return self.rows.pop(0) if self.rows else []


def intent(**kwargs):
    values = dict(
        id=UUID(int=1),
        record_id=UUID(int=2),
        submission_id=UUID(int=3),
        subject_revision=UUID(int=4),
        recipient_id=UUID(int=5),
        attempts=0,
    )
    return worker.Intent(**(values | kwargs))


@pytest.mark.parametrize(
    'attempts,seconds,status', [(0, 60, 'pending'), (1, 120, 'pending'), (7, 3600, 'failed')]
)
def test_retry_is_bounded_sanitized_and_clock_controlled(attempts, seconds, status):
    cur = Cursor()
    assert worker._retry(cur, site_id='site-a', items=[intent(attempts=attempts)], now=NOW) == {
        'failed': int(status == 'failed'),
        'retry': int(status != 'failed'),
    }
    sql, params = cur.calls[-1]
    assert 'site_id=%s' in sql and 'attempts<8' in sql
    assert status in params and NOW + timedelta(seconds=seconds) in params
    assert 'review_delivery_unavailable' in params


def test_receipt_is_unique_and_has_no_private_content():
    cur = Cursor()
    worker._receipt(cur, site_id='site-a', recipient_id=UUID(int=5), now=NOW, intent_id=UUID(int=1))
    sql, params = cur.calls[-1]
    assert 'ON CONFLICT (effect_key) DO NOTHING' in sql
    assert 'review:intent:site-a:00000000-0000-0000-0000-000000000001' in params
    assert 'body' not in sql and 'email' not in sql


def test_missing_or_stale_subject_suppresses_without_identity_lookup():
    cur = Cursor([None])
    assert (
        worker._decision(cur, site_id='site-a', item=intent(), policy={'require_review': True})
        == 'ineligible'
    )
    assert len(cur.calls) == 1


@pytest.mark.parametrize('mode', ['immediate', 'digest', 'disabled', 'unexpected'])
def test_live_preference_is_closed_and_independent(monkeypatch, mode):
    cur = Cursor(
        [
            (
                'in_review',
                None,
                1,
                UUID(int=4),
                UUID(int=3),
                UUID(int=7),
                UUID(int=8),
                UUID(int=9),
                False,
                'a' * 64,
            ),
            (mode,),
        ]
    )
    monkeypatch.setattr(worker.policy_repository, 'current_fingerprint', lambda *a, **k: 'a' * 64)
    monkeypatch.setattr(
        worker.policy_repository, 'member', lambda *a, **k: {'organization_id': 'org'}
    )
    result = worker._decision(
        cur,
        site_id='site-a',
        item=intent(),
        policy={'require_review': True, 'organization_id': 'org'},
    )
    assert result == (mode if mode in {'immediate', 'digest', 'disabled'} else 'ineligible')


def test_author_cannot_receive_even_if_privileged(monkeypatch):
    cur = Cursor(
        [
            (
                'in_review',
                None,
                1,
                UUID(int=4),
                UUID(int=3),
                UUID(int=5),
                UUID(int=8),
                UUID(int=9),
                False,
                'a' * 64,
            )
        ]
    )
    assert (
        worker._decision(cur, site_id='site-a', item=intent(), policy={'require_review': True})
        == 'ineligible'
    )


def test_next_digest_is_next_utc_day_and_closed_day_moves_forward():
    cur = Cursor([(UUID(int=10), 'closed', 1), (UUID(int=11), 'open', 0)])
    worker._assign_digest(cur, site_id='site-a', item=intent(), now=NOW)
    assert cur.calls[0][1][-1] == (NOW + timedelta(days=1)).date()
    assert any((NOW + timedelta(days=2)).date() in params for _, params in cur.calls)
    assert 'digest_batch_id IS NULL' in cur.calls[-1][0]


class Connection:
    def __init__(self, cur):
        self.cur, self.commits, self.rollbacks = cur, 0, 0

    def cursor(self):
        from contextlib import nullcontext

        return nullcontext(self.cur)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def bind(monkeypatch, rows):
    from contextlib import contextmanager

    cur = Cursor(rows)
    conn = Connection(cur)
    scopes = []

    @contextmanager
    def database(*, tenant_id):
        scopes.append(tenant_id)
        yield conn

    monkeypatch.setattr(worker, 'db_conn', database)
    monkeypatch.setattr(
        worker.policy_repository, 'read_policy', lambda *a, **k: {'require_review': True}
    )
    return cur, conn, scopes


def row(item=None):
    from dataclasses import astuple

    return astuple(item or intent())


@pytest.mark.parametrize(
    'mode,expected',
    [
        ('immediate', 'delivered'),
        ('disabled', 'suppressed'),
        ('ineligible', 'suppressed'),
        ('digest', 'digest'),
    ],
)
def test_worker_transactions_local_only_and_scope(monkeypatch, mode, expected):
    import socket

    def forbidden(*a, **k):
        raise AssertionError('network must never be used')

    monkeypatch.setattr(socket, 'socket', forbidden)
    rows = [[row()], None, []] if mode == 'digest' else [[row()], []]
    cur, conn, scopes = bind(monkeypatch, rows)
    monkeypatch.setattr(worker, '_decision', lambda *a, **k: mode)
    result = worker.process_review_notifications(site_id='site-a', now=NOW)
    assert result[expected] == 1 and result['adapter'] == 'local_test'
    assert conn.commits == 1 and conn.rollbacks == 0 and scopes == ['site-a']
    assert 'pg_advisory_xact_lock' in cur.calls[0][0]
    assert 'FOR UPDATE SKIP LOCKED' in cur.calls[1][0]
    assert any('SAVEPOINT' in sql for sql, _ in cur.calls)


@pytest.mark.parametrize('attempts,expected', [(0, 'retry'), (7, 'failed')])
def test_effect_error_rolls_back_before_durable_retry(monkeypatch, attempts, expected):
    cur, conn, _ = bind(monkeypatch, [[row(intent(attempts=attempts))], []])

    def outage(*a, **k):
        raise RuntimeError('private database diagnostic')

    monkeypatch.setattr(worker, '_decision', outage)
    result = worker.process_review_notifications(site_id='site-a', now=NOW)
    assert result[expected] == 1 and conn.commits == 1
    rollback = next(i for i, (sql, _) in enumerate(cur.calls) if 'ROLLBACK TO' in sql)
    retry = next(i for i, (sql, _) in enumerate(cur.calls) if 'attempts=attempts+1' in sql)
    assert rollback < retry
    assert 'private database diagnostic' not in str(cur.calls) + str(result)


def test_process_crash_rolls_back_whole_transaction(monkeypatch):
    cur, conn, _ = bind(monkeypatch, [[row()]])

    def crash(*a, **k):
        raise KeyboardInterrupt()

    monkeypatch.setattr(worker, '_decision', crash)
    with pytest.raises(KeyboardInterrupt):
        worker.process_review_notifications(site_id='site-a', now=NOW)
    assert conn.commits == 0  # Real connection context rolls back on process/connection loss.


def test_database_failure_not_reported_delivered(monkeypatch):
    _, conn, _ = bind(monkeypatch, [])

    def unavailable(*a, **k):
        raise RuntimeError('unavailable')

    monkeypatch.setattr(worker.policy_repository, 'read_policy', unavailable)
    with pytest.raises(RuntimeError):
        worker.process_review_notifications(site_id='site-a', now=NOW)
    assert conn.commits == 0 and conn.rollbacks == 1


@pytest.mark.parametrize('value', [0, 101, True, '1'])
def test_invalid_batch_bound_does_not_connect(value):
    with pytest.raises(ValueError):
        worker.process_review_notifications(site_id='site-a', limit=value)


def test_naive_clock_and_noncanonical_scope_rejected():
    with pytest.raises(ValueError):
        worker.process_review_notifications(site_id='site-a', now=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        worker.process_review_notifications(site_id=' site-a')
    with pytest.raises(TypeError):
        worker.process_review_notifications(site_id='site-a', adapter='smtp')
    with pytest.raises(TypeError):
        worker.process_review_notifications(site_id='site-a', recipient='x@example.test')


@pytest.mark.parametrize('mode', ['disabled', 'immediate', 'ineligible'])
def test_digest_recheck_suppresses_changed_preferences_or_access(monkeypatch, mode):
    cur, conn, _ = bind(monkeypatch, [[], [(UUID(int=10), UUID(int=5))], [row()]])
    monkeypatch.setattr(worker, '_decision', lambda *a, **k: mode)
    result = worker.process_review_notifications(site_id='site-a', now=NOW)
    assert result['suppressed'] == 1 and result['delivered'] == 0
    assert not any(
        'INSERT INTO sitecontent_reviewnotificationdelivery' in sql for sql, _ in cur.calls
    )
    assert conn.commits == 1


def test_digest_freezes_exact_membership_and_one_batch_receipt(monkeypatch):
    cur, conn, _ = bind(
        monkeypatch, [[], [(UUID(int=10), UUID(int=5))], [row(), row(intent(id=UUID(int=12)))]]
    )
    monkeypatch.setattr(worker, '_decision', lambda *a, **k: 'digest')
    result = worker.process_review_notifications(site_id='site-a', now=NOW)
    assert result['delivered'] == 2
    receipts = [
        params
        for sql, params in cur.calls
        if 'INSERT INTO sitecontent_reviewnotificationdelivery' in sql
    ]
    assert len(receipts) == 1 and receipts[0][4] is None and receipts[0][5] == str(UUID(int=10))
    assert any('digest_batch_id=%s' in sql and 'FOR UPDATE' in sql for sql, _ in cur.calls)


@pytest.mark.parametrize('attempts,outcome', [(0, 'retry'), (7, 'failed')])
def test_digest_effect_failure_preserves_closed_membership(monkeypatch, attempts, outcome):
    cur, conn, _ = bind(
        monkeypatch, [[], [(UUID(int=10), UUID(int=5))], [row(intent(attempts=attempts))]]
    )

    def fail(*a, **k):
        raise RuntimeError('sensitive')

    monkeypatch.setattr(worker, '_decision', fail)
    result = worker.process_review_notifications(site_id='site-a', now=NOW)
    assert result[outcome] == 1 and conn.commits == 1
    closed = next(i for i, (sql, _) in enumerate(cur.calls) if "SET status='closed'" in sql)
    savepoint = next(
        i for i, (sql, _) in enumerate(cur.calls) if sql == 'SAVEPOINT review_delivery'
    )
    assert closed < savepoint


def test_digest_overcapacity_fails_closed(monkeypatch):
    _, conn, _ = bind(monkeypatch, [[], [(UUID(int=10), UUID(int=5))], [row()] * 101])
    with pytest.raises(RuntimeError, match='membership_invalid'):
        worker.process_review_notifications(site_id='site-a', now=NOW)
    assert conn.commits == 0 and conn.rollbacks == 1


def test_digest_assignment_capacity_is_bounded():
    cur = Cursor([(UUID(int=10), 'closed', 1)] * 32)
    with pytest.raises(RuntimeError, match='capacity_unavailable'):
        worker._assign_digest(cur, site_id='site-a', item=intent(), now=NOW)
    assert len(cur.calls) == 32


@pytest.mark.parametrize('source', [{}, {'intent_id': UUID(int=1), 'batch_id': UUID(int=2)}])
def test_receipt_requires_exactly_one_source(source):
    with pytest.raises(ValueError):
        worker._receipt(Cursor(), site_id='site-a', recipient_id=UUID(int=5), now=NOW, **source)


@pytest.mark.parametrize(
    'change',
    [
        {0: 'draft'},
        {1: NOW},
        {2: 2},
        {3: UUID(int=44)},
        {4: UUID(int=33)},
        {5: None, 8: False},
        {6: None},
        {7: None},
        {6: UUID(int=5)},
        {7: UUID(int=5)},
    ],
)
def test_pending_revision_provenance_and_submission_are_rechecked(change):
    record = [
        'in_review',
        None,
        1,
        UUID(int=4),
        UUID(int=3),
        UUID(int=7),
        UUID(int=8),
        UUID(int=9),
        False,
        'a' * 64,
    ]
    for index, value in change.items():
        record[index] = value
    assert (
        worker._decision(
            Cursor([record]), site_id='site-a', item=intent(), policy={'require_review': True}
        )
        == 'ineligible'
    )


@pytest.mark.parametrize('reason', ['fingerprint', 'membership', 'organization'])
def test_revocation_policy_and_fingerprint_suppress(monkeypatch, reason):
    cur = Cursor(
        [
            (
                'in_review',
                None,
                1,
                UUID(int=4),
                UUID(int=3),
                UUID(int=7),
                UUID(int=8),
                UUID(int=9),
                False,
                'a' * 64,
            )
        ]
    )
    monkeypatch.setattr(
        worker.policy_repository,
        'current_fingerprint',
        lambda *a, **k: 'b' * 64 if reason == 'fingerprint' else 'a' * 64,
    )

    def member(*a, **k):
        if reason == 'membership':
            raise PermissionError()
        return {'organization_id': 'other'}

    monkeypatch.setattr(worker.policy_repository, 'member', member)
    assert (
        worker._decision(
            cur,
            site_id='site-a',
            item=intent(),
            policy={'require_review': True, 'organization_id': 'org'},
        )
        == 'ineligible'
    )


def test_all_suppressed_batch_is_closed_not_delivered_and_not_pending(monkeypatch):
    cur, _, _ = bind(monkeypatch, [[], [(UUID(int=10), UUID(int=5))], [row()]])
    monkeypatch.setattr(worker, '_decision', lambda *a, **k: 'disabled')
    result = worker.process_review_notifications(site_id='site-a', now=NOW)
    assert result['delivered'] == 0 and result['suppressed'] == 1
    assert cur.calls[-2][1][:2] == ('closed', None)
    due_query = next(sql for sql, _ in cur.calls if 'SELECT b.id,b.recipient_id' in sql)
    assert 'AND EXISTS' in due_query and "i.status='digest'" in due_query


def test_mixed_terminal_and_retry_attempts_count_each_intent(monkeypatch):
    cur, _, _ = bind(
        monkeypatch,
        [
            [],
            [(UUID(int=10), UUID(int=5))],
            [row(intent(attempts=7)), row(intent(id=UUID(int=22), attempts=0))],
        ],
    )

    def outage(*a, **k):
        raise RuntimeError('outage')

    monkeypatch.setattr(worker, '_decision', outage)
    result = worker.process_review_notifications(site_id='site-a', now=NOW)
    assert result['failed'] == 1 and result['retry'] == 1
    assert not any("SET status='failed'" in sql for sql, _ in cur.calls)


@pytest.mark.parametrize(
    'required,author,submitter,expected',
    [
        (False, 5, 9, 'immediate'),
        (False, 8, 5, 'ineligible'),
        (False, None, 9, 'immediate'),
        (False, 8, None, 'ineligible'),
        (True, 5, 9, 'ineligible'),
        (True, 8, 9, 'immediate'),
    ],
)
def test_current_policy_selects_optional_publisher_or_independent_reviewer(
    monkeypatch, required, author, submitter, expected
):
    cur = Cursor(
        [
            (
                'in_review',
                None,
                1,
                UUID(int=4),
                UUID(int=3),
                UUID(int=5),
                UUID(int=author) if author else None,
                UUID(int=submitter) if submitter else None,
                False,
                'a' * 64,
            ),
            ('immediate',),
        ]
    )
    if required and author == 8:
        cur.rows[0] = (*cur.rows[0][:5], UUID(int=7), *cur.rows[0][6:])
    monkeypatch.setattr(worker.policy_repository, 'current_fingerprint', lambda *a, **k: 'a' * 64)
    permissions = []

    def member(*a, **kwargs):
        permissions.append(kwargs['permission'])
        return {'organization_id': 'org'}

    monkeypatch.setattr(worker.policy_repository, 'member', member)
    assert (
        worker._decision(
            cur,
            site_id='site-a',
            item=intent(),
            policy={'require_review': required, 'organization_id': 'org'},
        )
        == expected
    )
    if expected == 'immediate':
        assert permissions == ['review' if required else 'publish']


@pytest.mark.parametrize(
    'before,after,expected', [(True, False, 'immediate'), (False, True, 'ineligible')]
)
def test_delivery_rechecks_both_policy_flip_directions(monkeypatch, before, after, expected):
    # Intent has no cached audience authorization: current policy wins, without backfill.
    cur = Cursor(
        [
            (
                'in_review',
                None,
                1,
                UUID(int=4),
                UUID(int=3),
                UUID(int=5),
                UUID(int=5),
                UUID(int=9),
                False,
                'a' * 64,
            ),
            ('immediate',),
        ]
    )
    monkeypatch.setattr(worker.policy_repository, 'current_fingerprint', lambda *a, **k: 'a' * 64)
    monkeypatch.setattr(
        worker.policy_repository, 'member', lambda *a, **k: {'organization_id': 'org'}
    )
    policy = {'require_review': before, 'organization_id': 'org'}
    policy['require_review'] = after
    assert worker._decision(cur, site_id='site-a', item=intent(), policy=policy) == expected


def test_no_recipient_intents_never_claim_local_delivery(monkeypatch):
    cur, conn, _ = bind(monkeypatch, [[], []])
    result = worker.process_review_notifications(site_id='site-a', now=NOW)
    assert result == dict(
        adapter='local_test', delivered=0, digest=0, suppressed=0, retry=0, failed=0
    )
    assert not any(
        'INSERT INTO sitecontent_reviewnotificationdelivery' in sql for sql, _ in cur.calls
    )
    assert conn.commits == 1


def test_optional_request_tolerates_unknown_historical_authorship(monkeypatch):
    cur = Cursor(
        [
            (
                'in_review',
                None,
                1,
                UUID(int=4),
                UUID(int=3),
                None,
                None,
                UUID(int=9),
                False,
                'a' * 64,
            ),
            ('immediate',),
        ]
    )
    monkeypatch.setattr(worker.policy_repository, 'current_fingerprint', lambda *a, **k: 'a' * 64)
    monkeypatch.setattr(
        worker.policy_repository, 'member', lambda *a, **k: {'organization_id': 'org'}
    )
    assert (
        worker._decision(
            cur,
            site_id='site-a',
            item=intent(),
            policy={'require_review': False, 'organization_id': 'org'},
        )
        == 'immediate'
    )
