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
        runtime.configured_tenants(','.join(f'tenant-{index}' for index in range(17)))


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


def due_alert(*, attempts=0, expires_at=None):
    return {
        'deliveryId': str(UUID(int=1)),
        'attempts': attempts,
        'maximumAttempts': 5,
        'expiresAt': expires_at or NOW + timedelta(minutes=15),
        'incidentFingerprint': 'c' * 64,
        'severity': 'high',
        'summaryCode': 'api.unavailable',
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
    result = runtime.dispatch_alerts(
        tenant_id='tenant-one', sender=MagicMock(), now=NOW
    )
    assert result == {'due': 2, 'sent': 0, 'deferred': 1, 'terminal': 1}
    assert [call.kwargs['error_code'] for call in update.call_args_list] == [
        'delivery.expired',
        'delivery.key-unavailable',
    ]


def test_configured_adapters_cover_the_whole_catalog():
    catalog = __import__('json').loads(runtime.CATALOG.read_text())
    assert set(runtime.configured_probe_adapters()) == {probe['id'] for probe in catalog['probes']}
