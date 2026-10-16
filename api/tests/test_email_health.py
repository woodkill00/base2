import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from api.services import email_health as health

NOW = datetime(2026, 10, 16, tzinfo=UTC)


@pytest.mark.parametrize('attention', [False, True])
def test_worker_publishes_only_sanitized_status(monkeypatch, attention):
    client = MagicMock()
    monkeypatch.setattr(health.redis_client, 'get_client', lambda: client)
    monkeypatch.setattr(health, '_outbox_requires_attention', lambda: attention)
    monkeypatch.setattr(health, '_configuration_ready', lambda: True)
    health.publish_email_health(now=NOW)
    value = json.loads(client.set.call_args.args[1])
    assert set(value) == {'observedAt', 'deploymentEpoch', 'code'}
    assert value['code'] == ('email.outbox-attention' if attention else 'email.transport-ready')
    assert client.set.call_args.kwargs['ex'] == 180


def test_observation_failure_is_visible_without_exception_content(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(health.redis_client, 'get_client', lambda: client)
    monkeypatch.setattr(health, '_configuration_ready', lambda: True)
    monkeypatch.setattr(
        health, '_outbox_requires_attention', MagicMock(side_effect=ValueError('secret-reset-link'))
    )
    with pytest.raises(RuntimeError, match='email_health_observation_failed'):
        health.publish_email_health(now=NOW)
    assert 'secret-reset-link' not in client.set.call_args.args[1]
    assert json.loads(client.set.call_args.args[1])['code'] == 'email.observation-failed'


def test_invalid_configuration_publishes_degradation_without_query(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(health.redis_client, 'get_client', lambda: client)
    monkeypatch.setattr(health, '_configuration_ready', lambda: False)
    query = MagicMock()
    monkeypatch.setattr(health, '_outbox_requires_attention', query)
    health.publish_email_health(now=NOW)
    assert json.loads(client.set.call_args.args[1])['code'] == 'email.not-configured'
    query.assert_not_called()


@pytest.mark.parametrize(
    'mutation', ['missing', 'bad-json', 'extra', 'stale', 'future', 'epoch', 'hostile', 'oversize']
)
def test_reader_rejects_invalid_observations(monkeypatch, mutation):
    value = {
        'observedAt': NOW.isoformat(),
        'deploymentEpoch': 'development',
        'code': 'email.transport-ready',
    }
    if mutation == 'extra':
        value['recipient'] = 'private@example.com'
    if mutation == 'stale':
        value['observedAt'] = (NOW - timedelta(seconds=121)).isoformat()
    if mutation == 'future':
        value['observedAt'] = (NOW + timedelta(seconds=1)).isoformat()
    if mutation == 'epoch':
        value['deploymentEpoch'] = 'old-deployment'
    if mutation == 'hostile':
        value['code'] = 'secret-reset-link'
    raw = json.dumps(value)
    if mutation == 'missing':
        raw = None
    if mutation == 'bad-json':
        raw = '{'
    if mutation == 'oversize':
        raw = ' ' * 4097
    client = MagicMock()
    client.get.return_value = raw
    monkeypatch.setattr(health.redis_client, 'get_client', lambda: client)
    assert health.email_health_probe(now=NOW) == ('degraded', 'email.observation-stale', 0)


@pytest.mark.parametrize(
    'code',
    [
        'email.transport-ready',
        'email.outbox-attention',
        'email.not-configured',
        'email.observation-failed',
    ],
)
def test_reader_accepts_only_closed_codes(monkeypatch, code):
    client = MagicMock()
    client.get.return_value = json.dumps(
        {'observedAt': NOW.isoformat(), 'deploymentEpoch': 'development', 'code': code}
    ).encode()
    monkeypatch.setattr(health.redis_client, 'get_client', lambda: client)
    expected = 'healthy' if code == 'email.transport-ready' else 'degraded'
    assert health.email_health_probe(now=NOW) == (expected, code, 0)


def test_reader_never_exposes_redis_failure(monkeypatch):
    monkeypatch.setattr(
        health.redis_client, 'get_client', MagicMock(side_effect=RuntimeError('private'))
    )
    assert health.email_health_probe(now=NOW)[1] == 'email.observation-stale'


def test_operations_requires_both_transport_and_delivery_receipt(monkeypatch):
    from api.services import operations_runtime as runtime

    monkeypatch.setattr(
        runtime, 'email_health_probe', lambda: ('degraded', 'email.outbox-attention', 0)
    )
    receipt = MagicMock(return_value=('healthy', 'email.ready', 0))
    monkeypatch.setattr(runtime, '_receipt', receipt)
    assert runtime.configured_probe_adapters()['email.delivery'](5)[1] == 'email.outbox-attention'
    receipt.assert_not_called()
    monkeypatch.setattr(
        runtime, 'email_health_probe', lambda: ('healthy', 'email.transport-ready', 0)
    )
    assert runtime.configured_probe_adapters()['email.delivery'](5)[1] == 'email.ready'
    receipt.assert_called_once_with('email', 5)


def test_database_observer_is_read_only_bounded_and_has_no_message_fields(monkeypatch):
    from api import db

    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (True,)
    context = MagicMock()
    context.__enter__.return_value = connection
    monkeypatch.setattr(db, 'db_conn', lambda: context)
    assert health._outbox_requires_attention() is True
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert statements[0] == "SET LOCAL statement_timeout = '2000ms'"
    assert 'SELECT EXISTS' in statements[1]
    for forbidden in ('to_email', 'body_text', 'body_html', 'DELETE', 'UPDATE', 'INSERT'):
        assert forbidden not in statements[1]
    cursor.fetchone.return_value = None
    with pytest.raises(RuntimeError, match='query_invalid'):
        health._outbox_requires_attention()


def test_configuration_validation_never_sends(monkeypatch):
    from api.services import email_service

    adapter = MagicMock(name='adapter')
    adapter.name = 'resend'
    monkeypatch.setattr(email_service, '_configured_adapter', lambda: adapter)
    assert health._configuration_ready() is True
    adapter.send.assert_not_called()
    adapter.name = 'disabled'
    assert health._configuration_ready() is False
    monkeypatch.setattr(
        email_service, '_configured_adapter', MagicMock(side_effect=ValueError('secret'))
    )
    assert health._configuration_ready() is False


def test_publication_failure_is_sanitized_and_visible(monkeypatch):
    monkeypatch.setattr(health, '_configuration_ready', lambda: False)
    monkeypatch.setattr(
        health.redis_client, 'get_client', MagicMock(side_effect=RuntimeError('secret'))
    )
    with pytest.raises(RuntimeError, match='^email_health_publication_failed$'):
        health.publish_email_health(now=NOW)


def test_rejected_redis_write_is_not_reported_as_success(monkeypatch):
    client = MagicMock()
    client.set.return_value = False
    monkeypatch.setattr(health, '_configuration_ready', lambda: False)
    monkeypatch.setattr(health.redis_client, 'get_client', lambda: client)
    with pytest.raises(RuntimeError, match='email_health_publication_failed'):
        health.publish_email_health(now=NOW)
