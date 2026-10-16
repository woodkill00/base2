import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from api.services.email_send_budget import reserve_send


def ledger(tmp_path, **changes):
    path = tmp_path / 'budget.json'
    state = {'schemaVersion': 1, 'expiresAt': 2000, 'maxAttempts': 2, 'reservations': []}
    state.update(changes)
    path.write_text(json.dumps(state))
    path.chmod(0o600)
    return path


def test_durable_cap_and_duplicate_reservation(tmp_path):
    path = ledger(tmp_path)
    reserve_send(str(path), 'one', now=1000)
    with pytest.raises(RuntimeError, match='email_budget_duplicate'):
        reserve_send(str(path), 'one', now=1000)
    reserve_send(str(path), 'two', now=1000)
    with pytest.raises(RuntimeError, match='email_budget_exhausted'):
        reserve_send(str(path), 'three', now=1000)
    assert 'one' not in path.read_text()


def test_concurrent_reservations_cannot_exceed_cap(tmp_path):
    path = ledger(tmp_path, maxAttempts=1)

    def attempt(key):
        try:
            reserve_send(str(path), str(key), now=1000)
            return True
        except RuntimeError:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(attempt, range(8))) == 1


@pytest.mark.parametrize(
    'changes',
    [
        {'expiresAt': 1000},
        {'expiresAt': 999999},
        {'maxAttempts': 0},
        {'maxAttempts': True},
        {'reservations': ['invalid']},
        {'extra': 'field'},
    ],
)
def test_invalid_or_expired_budget_fails_closed(tmp_path, changes):
    path = ledger(tmp_path, **changes)
    with pytest.raises(RuntimeError, match='email_budget_'):
        reserve_send(str(path), 'one', now=1000)


def test_missing_corrupt_symlink_or_public_ledger_fails_closed(tmp_path):
    path = tmp_path / 'missing'
    with pytest.raises(RuntimeError):
        reserve_send(str(path), 'one', now=1000)
    path = ledger(tmp_path)
    link = tmp_path / 'link'
    link.symlink_to(path)
    with pytest.raises(RuntimeError):
        reserve_send(str(link), 'one', now=1000)
    path.chmod(0o644)
    with pytest.raises(RuntimeError):
        reserve_send(str(path), 'one', now=1000)
    path.chmod(0o600)
    path.write_text('partial write')
    with pytest.raises(RuntimeError):
        reserve_send(str(path), 'one', now=1000)
