import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from api.services import operations_runtime as runtime

NOW = datetime(2026, 9, 8, tzinfo=UTC)
ALERT_KEY = b'a' * 32
RECEIPT_KEY = b'b' * 32


def test_configured_tenants_are_bounded_canonical_and_deduplicated():
    assert runtime.configured_tenants('tenant-one,tenant-two,tenant-one') == [
        'tenant-one',
        'tenant-two',
    ]
    with pytest.raises(ValueError):
        runtime.configured_tenants('../escape')
    with pytest.raises(ValueError):
        runtime.configured_tenants(','.join(f'tenant-{index}' for index in range(33)))


def test_fair_tenant_batch_rotates_without_exceeding_worker_capacity(monkeypatch):
    client = MagicMock()
    client.incrby.side_effect = [2, 4]
    monkeypatch.setattr(runtime.redis_client, 'get_client', lambda: client)
    tenants = ['tenant-one', 'tenant-two', 'tenant-three']
    assert runtime.fair_tenant_batch(tenants, limit=2) == ['tenant-one', 'tenant-two']
    assert runtime.fair_tenant_batch(tenants, limit=2) == ['tenant-three', 'tenant-one']
    with pytest.raises(ValueError, match='batch_invalid'):
        runtime.fair_tenant_batch(tenants, limit=17)


def test_internal_http_is_allowlisted_bounded_and_reports_transport_failure(monkeypatch):
    monkeypatch.setenv('OPERATIONS_INTERNAL_BASE_URL', 'https://external.example')
    assert runtime._internal_http('/api/health', 2) == (
        'degraded',
        'http.not-configured',
        0,
    )

    response = MagicMock(status=204)
    response.__enter__.return_value = response
    monkeypatch.setenv('OPERATIONS_INTERNAL_BASE_URL', 'http://nginx')
    monkeypatch.setattr(runtime, 'urlopen', MagicMock(return_value=response))
    assert runtime._internal_http('/api/health', 2)[:2] == ('healthy', 'http.ready')
    runtime.urlopen.side_effect = OSError('offline')
    assert runtime._internal_http('/api/health', 2)[:2] == (
        'unavailable',
        'http.unavailable',
    )


def test_timing_heartbeats_and_queue_observations_are_bounded(monkeypatch):
    moments = iter((1.0, 1.125, 2.0, 5.0))
    monkeypatch.setattr(runtime.time, 'monotonic', lambda: next(moments))
    assert runtime._timed(lambda: True, 'ready', 'failed', 1) == ('healthy', 'ready', 125)
    assert runtime._timed(lambda: False, 'ready', 'failed', 1) == (
        'unavailable',
        'failed',
        1000,
    )

    client = MagicMock()
    monkeypatch.setattr(runtime.redis_client, 'get_client', lambda: client)
    monkeypatch.setenv('BASE2_DEPLOYMENT_EPOCH', 'release-106')
    runtime.mark_runtime_heartbeat('workers:runtime-worker', now=NOW)
    heartbeat_payload = json.loads(client.set.call_args.args[1])
    client.set.assert_called_with(
        runtime.redis_client.key('operations', 'workers:runtime-worker'),
        client.set.call_args.args[1],
        ex=180,
    )
    assert heartbeat_payload == {
        'observedAt': NOW.isoformat(),
        'deploymentEpoch': 'release-106',
    }
    runtime.mark_queue_observation(published_at=NOW - timedelta(seconds=3), now=NOW)
    queue_payload = json.loads(client.set.call_args.args[1])
    assert queue_payload == {'observedAt': NOW.isoformat(), 'delayMs': 3000}


def test_runtime_heartbeat_and_queue_probe_fail_closed_on_invalid_evidence(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(runtime.redis_client, 'get_client', lambda: client)
    monkeypatch.setenv('BASE2_DEPLOYMENT_EPOCH', 'current-release')
    client.get.return_value = json.dumps({
        'observedAt': datetime.now(UTC).isoformat(),
        'deploymentEpoch': 'current-release',
    }).encode()
    assert runtime._runtime_heartbeat('workers:email-worker', 30)[:2] == (
        'healthy',
        'workers:email-worker.ready',
    )
    client.get.return_value = json.dumps({
        'observedAt': datetime.now(UTC).isoformat(),
        'deploymentEpoch': 'previous-release',
    }).encode()
    assert runtime._runtime_heartbeat('workers:email-worker', 30)[0] == 'degraded'
    client.get.return_value = b'not-a-timestamp'
    assert runtime._runtime_heartbeat('workers:email-worker', 1)[:2] == (
        'degraded',
        'workers:email-worker.stale',
    )
    client.llen.side_effect = RuntimeError('redis unavailable')
    assert runtime._queue_health(1) == ('degraded', 'queues.unknown', 0)


def test_collect_site_connects_catalog_adapters_and_persistence(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        runtime,
        'collect_probe_results',
        lambda **kwargs: captured.update(kwargs) or [{'probeId': 'api.health'}],
    )
    monkeypatch.setattr(
        runtime.operations,
        'record_probe_batch',
        lambda **kwargs: captured.update({'persisted': kwargs}) or {'samples': 1},
    )
    adapters = {'api.health': object()}
    result = runtime.collect_site(
        tenant_id='tenant-one', environment='staging', now=NOW, adapters=adapters
    )
    assert result == {'samples': 1}
    assert captured['adapters'] is adapters
    assert captured['persisted'] == {
        'tenant_id': 'tenant-one',
        'environment': 'staging',
        'results': [{'probeId': 'api.health'}],
        'now': NOW,
    }


def test_live_collection_holds_and_conditionally_releases_a_tenant_lock(monkeypatch):
    client = MagicMock()
    client.set.return_value = True
    monkeypatch.setattr(runtime.redis_client, 'get_client', lambda: client)
    monkeypatch.setattr(
        runtime, 'configured_probe_adapters', lambda _tenant: {'api.health': object()}
    )
    monkeypatch.setattr(runtime, 'collect_probe_results', lambda **kwargs: [])
    monkeypatch.setattr(runtime.operations, 'record_probe_batch', lambda **kwargs: {'samples': 0})
    heartbeat = MagicMock()
    monkeypatch.setattr(runtime, 'mark_runtime_heartbeat', heartbeat)
    assert runtime.collect_site(tenant_id='tenant-one', environment='staging', now=NOW) == {
        'samples': 0
    }
    assert client.set.call_args.kwargs == {'nx': True, 'ex': 120}
    client.eval.assert_called_once()
    heartbeat.assert_called_once_with('monitoring:tenant-one', now=NOW)

    client.set.return_value = False
    with pytest.raises(RuntimeError, match='collection_in_progress'):
        runtime.collect_site(tenant_id='tenant-one', environment='staging', now=NOW)


def test_queue_probe_uses_worker_liveness_depth_and_observed_delay(monkeypatch):
    client = MagicMock()
    client.llen.return_value = 0
    monkeypatch.setattr(runtime.redis_client, 'get_client', lambda: client)
    monkeypatch.setattr(runtime, '_runtime_heartbeat', lambda name, timeout: ('healthy', '', 0))
    assert runtime._queue_health(1) == ('healthy', 'queues.empty', 0)

    now = datetime.now(UTC)
    client.llen.return_value = 4
    client.get.return_value = json.dumps({'observedAt': now.isoformat(), 'delayMs': 1200})
    assert runtime._queue_health(1) == ('healthy', 'queues.ready', 1200)

    monkeypatch.setattr(runtime, '_runtime_heartbeat', lambda name, timeout: ('degraded', '', 0))
    assert runtime._queue_health(1) == ('degraded', 'queues.delayed', 1200)


def test_monitoring_self_probe_is_tenant_specific(monkeypatch):
    heartbeat = MagicMock(return_value=('healthy', 'monitoring.ready', 0))
    monkeypatch.setattr(runtime, '_runtime_heartbeat', heartbeat)
    runtime.configured_probe_adapters('tenant-one')['monitoring.self'](1)
    heartbeat.assert_called_once_with('monitoring:tenant-one', 1)


def due_alert(*, attempts=0, expires_at=None):
    return {
        'deliveryId': str(UUID(int=1)),
        'attempts': attempts,
        'maximumAttempts': 5,
        'expiresAt': expires_at or NOW + timedelta(minutes=15),
        'incidentFingerprint': 'c' * 64,
        'severity': 'high',
        'summaryCode': 'api.unavailable',
        'claimToken': str(UUID(int=9)),
    }


def test_dispatch_sends_once_and_records_integrity_receipt(monkeypatch):
    monkeypatch.setattr(runtime.operations, 'due_alert_deliveries', lambda **kwargs: [due_alert()])
    update = MagicMock(return_value=True)
    monkeypatch.setattr(runtime.operations, 'update_alert_delivery', update)
    result = runtime.dispatch_alerts(
        tenant_id='tenant-one',
        sender=lambda payload: 'discord.receipt-1',
        now=NOW,
        integrity_key=ALERT_KEY,
        receipt_key=RECEIPT_KEY,
    )
    assert result == {'due': 1, 'sent': 1, 'deferred': 0, 'terminal': 0}
    assert update.call_args.kwargs['status'] == 'sent'
    assert len(update.call_args.kwargs['receipt_digest']) == 64


def test_dispatch_provider_loss_is_durable_bounded_and_visible(monkeypatch):
    monkeypatch.setattr(
        runtime.operations, 'due_alert_deliveries', lambda **kwargs: [due_alert(attempts=4)]
    )
    update = MagicMock(return_value=True)
    monkeypatch.setattr(runtime.operations, 'update_alert_delivery', update)
    result = runtime.dispatch_alerts(
        tenant_id='tenant-one',
        sender=lambda payload: (_ for _ in ()).throw(RuntimeError('offline')),
        now=NOW,
        integrity_key=ALERT_KEY,
        receipt_key=RECEIPT_KEY,
    )
    assert result == {'due': 1, 'sent': 0, 'deferred': 0, 'terminal': 1}
    assert update.call_args.kwargs['status'] == 'failed'
    assert update.call_args.kwargs['error_code'] == 'delivery.provider_failed'


def test_empty_alert_queue_does_not_read_keys_or_call_sender(monkeypatch):
    monkeypatch.setattr(runtime.operations, 'due_alert_deliveries', lambda **kwargs: [])
    sender = MagicMock()
    assert runtime.dispatch_alerts(tenant_id='tenant-one', sender=sender, now=NOW) == {
        'due': 0,
        'sent': 0,
        'deferred': 0,
        'terminal': 0,
    }
    sender.assert_not_called()


def test_expired_alert_and_missing_keys_are_terminal_or_backed_off(monkeypatch):
    monkeypatch.setattr(
        runtime.operations,
        'due_alert_deliveries',
        lambda **kwargs: [
            due_alert(attempts=0, expires_at=NOW),
            {**due_alert(attempts=0), 'deliveryId': str(UUID(int=2))},
        ],
    )
    update = MagicMock(return_value=True)
    monkeypatch.setattr(runtime.operations, 'update_alert_delivery', update)
    monkeypatch.delenv('OPERATIONS_ALERT_INTEGRITY_KEY', raising=False)
    result = runtime.dispatch_alerts(tenant_id='tenant-one', sender=MagicMock(), now=NOW)
    assert result == {'due': 2, 'sent': 0, 'deferred': 1, 'terminal': 1}
    assert [call.kwargs['error_code'] for call in update.call_args_list] == [
        'delivery.expired',
        'delivery.key-unavailable',
    ]


def test_configured_adapters_cover_the_whole_catalog():
    catalog = __import__('json').loads(runtime.CATALOG.read_text())
    assert set(runtime.configured_probe_adapters()) == {probe['id'] for probe in catalog['probes']}


def test_runtime_receipt_requires_fresh_exact_hmac_evidence(monkeypatch, tmp_path):
    key = b'r' * 32
    key_file = tmp_path / 'receipt.key'
    key_file.write_text(base64.urlsafe_b64encode(key).decode(), encoding='utf-8')
    key_file.chmod(0o600)
    monkeypatch.setattr(runtime.settings, 'OPERATIONS_RECEIPT_INTEGRITY_KEY_FILE', str(key_file))
    monkeypatch.setenv('OPERATIONS_RECEIPT_ROOT', str(tmp_path))
    now = datetime.now(UTC)
    value = {
        'schemaVersion': 1,
        'kind': 'backup',
        'status': 'passed',
        'sourceCommit': 'a' * 40,
        'artifactDigest': 'b' * 64,
        'observedAt': now.isoformat(),
        'expiresAt': (now + timedelta(minutes=5)).isoformat(),
    }
    value['digest'] = hmac.new(
        key,
        json.dumps(value, sort_keys=True, separators=(',', ':')).encode(),
        hashlib.sha256,
    ).hexdigest()
    (tmp_path / 'backup.json').write_text(json.dumps(value), encoding='utf-8')
    assert runtime._receipt('backup', 2)[:2] == ('healthy', 'backup.ready')
    value['sourceCommit'] = 'c' * 40
    (tmp_path / 'backup.json').write_text(json.dumps(value), encoding='utf-8')
    assert runtime._receipt('backup', 2)[:2] == ('degraded', 'backup.unknown')


def test_discord_sender_uses_stable_provider_deduplication_and_no_mentions(monkeypatch, tmp_path):
    webhook = tmp_path / 'webhook.url'
    webhook.write_text('https://discord.com/api/webhooks/123/token_value', encoding='utf-8')
    webhook.chmod(0o600)
    monkeypatch.setattr(runtime.settings, 'OPERATIONS_ALERT_WEBHOOK_URL_FILE', str(webhook))
    response = MagicMock(status=200)
    response.read.return_value = b'{"id":"987654321"}'
    response.__enter__.return_value = response
    opened = MagicMock(return_value=response)
    monkeypatch.setattr(runtime, 'urlopen', opened)
    payload = {
        'deliveryId': str(UUID(int=1)),
        'severity': 'high',
        'summaryCode': 'api.unavailable',
        'incidentId': 'a' * 64,
    }
    assert runtime.discord_webhook_sender(payload) == 'discord.987654321'
    request = opened.call_args.args[0]
    body = json.loads(request.data)
    assert body['enforce_nonce'] is True
    assert body['allowed_mentions'] == {'parse': []}
    assert body['nonce'] == hashlib.sha256(payload['deliveryId'].encode()).hexdigest()[:25]
