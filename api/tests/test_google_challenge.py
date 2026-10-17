from unittest.mock import MagicMock

import pytest

from api.security import google_challenge as challenge


def test_issue_is_private_bounded_and_atomically_single_use(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(challenge.redis_client, 'get_client', lambda: client)
    binding, nonce = challenge.issue()
    assert binding != nonce
    key = client.set.call_args.args[0]
    assert binding not in key
    assert client.set.call_args.kwargs == {'ex': 300, 'nx': True}
    client.getdel.side_effect = [nonce.encode(), None]
    assert challenge.consume(binding) == nonce
    with pytest.raises(ValueError, match='google_challenge_rejected'):
        challenge.consume(binding)
    assert client.getdel.call_args.args == (key,)


@pytest.mark.parametrize('value', ['', 'x', 'a' * 44, None, '../secret'])
def test_invalid_binding_never_reads_store(monkeypatch, value):
    client = MagicMock()
    monkeypatch.setattr(challenge.redis_client, 'get_client', lambda: client)
    with pytest.raises(ValueError, match='google_challenge_rejected'):
        challenge.consume(value)
    client.getdel.assert_not_called()


@pytest.mark.parametrize('value', [None, b'\xff', b'wrong', {}, 'a' * 44])
def test_missing_expired_or_malformed_nonce_rejected(monkeypatch, value):
    client = MagicMock()
    client.getdel.return_value = value
    monkeypatch.setattr(challenge.redis_client, 'get_client', lambda: client)
    with pytest.raises(ValueError, match='google_challenge_rejected'):
        challenge.consume('a' * 43)


@pytest.mark.parametrize('operation', ['issue', 'consume'])
def test_store_failure_is_closed_and_sanitized(monkeypatch, operation):
    monkeypatch.setattr(
        challenge.redis_client, 'get_client', MagicMock(side_effect=ValueError('secret'))
    )
    with pytest.raises(RuntimeError, match='^google_challenge_unavailable$'):
        challenge.issue() if operation == 'issue' else challenge.consume('a' * 43)


def test_rejected_write_cannot_issue_binding(monkeypatch):
    client = MagicMock()
    client.set.return_value = False
    monkeypatch.setattr(challenge.redis_client, 'get_client', lambda: client)
    with pytest.raises(RuntimeError, match='google_challenge_unavailable'):
        challenge.issue()
