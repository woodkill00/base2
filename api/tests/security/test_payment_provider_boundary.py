import hashlib
import hmac
import json

import pytest

from api.providers.payments import (
    LocalFakePaymentProvider,
    PaymentActivation,
    PaymentBoundaryError,
    WebhookActivation,
    verify_webhook,
)


def signed(body, timestamp='1000', secret=b'test-only-webhook-secret'):
    return hmac.new(secret, timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()


@pytest.mark.parametrize(
    'activation,error',
    [
        (PaymentActivation(), 'disabled'),
        (PaymentActivation(True, 'production', 'provider'), 'production_activation'),
        (PaymentActivation(True, 'sandbox', 'unknown'), 'not_allowlisted'),
        (PaymentActivation(True, 'local_fake', 'local_fake', 'secretref://bad'), 'must_not_read_credentials'),
    ],
)
def test_payment_activation_fails_closed(activation, error):
    with pytest.raises(PaymentBoundaryError, match=error):
        LocalFakePaymentProvider(activation)


def test_disabled_and_webhook_configuration_shapes_are_exact():
    PaymentActivation().validate()
    WebhookActivation().validate()
    with pytest.raises(PaymentBoundaryError, match='disabled_configuration'):
        PaymentActivation(False, 'disabled', 'none', 'secretref://bad').validate()
    with pytest.raises(PaymentBoundaryError, match='disabled_configuration'):
        WebhookActivation(False, 'disabled', 'secretref://bad', None).validate()
    with pytest.raises(PaymentBoundaryError, match='mode_not_allowlisted'):
        WebhookActivation(True, 'live-ish', 'secretref://base2/payment-webhook', 'approval-0123456789abcdef').validate()


def test_sandbox_webhook_requires_secretref_and_exact_approval_shape():
    valid = WebhookActivation(
        True, 'sandbox', 'secretref://base2/payment-webhook', 'approval-0123456789abcdef'
    )
    valid.validate()
    with pytest.raises(PaymentBoundaryError, match='secret_ref'):
        WebhookActivation(True, 'sandbox', 'plaintext', 'approval-0123456789abcdef').validate()
    with pytest.raises(PaymentBoundaryError, match='approval'):
        WebhookActivation(True, 'sandbox', 'secretref://base2/payment-webhook', None).validate()
    with pytest.raises(PaymentBoundaryError, match='separately_approved'):
        WebhookActivation(True, 'production', 'secretref://base2/payment-webhook', 'approval-0123456789abcdef').validate()


def test_signed_webhook_exact_replay_and_conflict():
    secret = b'test-only-webhook-secret'
    body = json.dumps({'type': 'payment.authorized'}).encode()
    store = set()
    first = verify_webhook(body=body, timestamp='1000', signature=signed(body), event_id='event_0001', secret=secret, replay_store=store, now=lambda: 1000)
    second = verify_webhook(body=body, timestamp='1000', signature=signed(body), event_id='event_0001', secret=secret, replay_store=store, now=lambda: 1000)
    assert first['replayed'] is False and second['replayed'] is True
    changed = json.dumps({'type': 'payment.refunded'}).encode()
    with pytest.raises(PaymentBoundaryError, match='event_conflict'):
        verify_webhook(body=changed, timestamp='1000', signature=signed(changed), event_id='event_0001', secret=secret, replay_store=store, now=lambda: 1000)


@pytest.mark.parametrize(
    'kwargs,error',
    [
        ({'timestamp': '1'}, 'stale'),
        ({'signature': '0' * 64}, 'invalid_signature'),
        ({'body': b'not-json'}, 'invalid_json'),
        ({'body': b'{"type":"customer.deleted"}'}, 'not_allowlisted'),
    ],
)
def test_hostile_webhooks_are_rejected(kwargs, error):
    secret = b'test-only-webhook-secret'
    body = kwargs.get('body', b'{"type":"payment.authorized"}')
    timestamp = kwargs.get('timestamp', '1000')
    signature = kwargs.get('signature', signed(body, timestamp, secret))
    with pytest.raises(PaymentBoundaryError, match=error):
        verify_webhook(body=body, timestamp=timestamp, signature=signature, event_id='event_0002', secret=secret, replay_store=set(), now=lambda: 1000)


def test_local_refund_cancel_transitions_and_idempotent_charge():
    provider = LocalFakePaymentProvider(PaymentActivation(True, 'local_fake', 'local_fake'))
    charge = provider.charge(tenant_id='site-a', amount_minor=100, currency='USD', replay_key='key-one')
    assert provider.charge(tenant_id='site-a', amount_minor=100, currency='USD', replay_key='key-one') == charge
    assert provider.refund(charge['paymentId'])['status'] == 'refunded'
    with pytest.raises(PaymentBoundaryError, match='invalid_transition'):
        provider.cancel(charge['paymentId'])

    other = provider.charge(tenant_id='site-a', amount_minor=200, currency='USD', replay_key='key-two')
    assert provider.cancel(other['paymentId'])['status'] == 'cancelled'
    with pytest.raises(PaymentBoundaryError, match='invalid_transition'):
        provider.refund(other['paymentId'])
    with pytest.raises(PaymentBoundaryError, match='invalid_charge'):
        provider.charge(tenant_id='', amount_minor=0, currency='usd', replay_key='')
    with pytest.raises(PaymentBoundaryError, match='not_found'):
        provider.cancel('fakepay_missing')
    with pytest.raises(PaymentBoundaryError, match='not_found'):
        provider.refund('fakepay_missing')


@pytest.mark.parametrize(
    'values,error',
    [
        ({'body': b'x' * 262145}, 'body_too_large'),
        ({'event_id': '../bad'}, 'invalid_event_id'),
        ({'timestamp': 'not-time'}, 'invalid_timestamp'),
    ],
)
def test_webhook_envelope_bounds(values, error):
    body = values.get('body', b'{"type":"payment.authorized"}')
    timestamp = values.get('timestamp', '1000')
    with pytest.raises(PaymentBoundaryError, match=error):
        verify_webhook(
            body=body,
            timestamp=timestamp,
            signature=signed(body, timestamp),
            event_id=values.get('event_id', 'event_0003'),
            secret=b'test-only-webhook-secret',
            replay_store=set(),
            now=lambda: 1000,
        )
