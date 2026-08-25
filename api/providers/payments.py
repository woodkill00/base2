from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, MutableSet


class PaymentBoundaryError(ValueError):
    """Stable failure for disabled, untrusted, or unauthorized payment behavior."""


SECRET_REF = re.compile(r'^secretref://[a-z0-9][a-z0-9/_-]{2,127}$')
EVENT_ID = re.compile(r'^[A-Za-z0-9_-]{8,128}$')


@dataclass(frozen=True)
class PaymentActivation:
    enabled: bool = False
    mode: str = 'disabled'
    provider: str = 'none'
    secret_ref: str | None = None

    def validate(self) -> None:
        if not self.enabled:
            if self.mode != 'disabled' or self.provider != 'none' or self.secret_ref is not None:
                raise PaymentBoundaryError('payment:disabled_configuration_invalid')
            return
        if self.mode == 'production':
            raise PaymentBoundaryError('payment:production_activation_separately_approved')
        if self.mode != 'local_fake' or self.provider != 'local_fake':
            raise PaymentBoundaryError('payment:provider_not_allowlisted')
        if self.secret_ref is not None:
            raise PaymentBoundaryError('payment:local_fake_must_not_read_credentials')


@dataclass(frozen=True)
class WebhookActivation:
    enabled: bool = False
    mode: str = 'disabled'
    secret_ref: str | None = None
    approval_receipt: str | None = None

    def validate(self) -> None:
        if not self.enabled:
            if self.mode != 'disabled' or self.secret_ref is not None or self.approval_receipt is not None:
                raise PaymentBoundaryError('webhook:disabled_configuration_invalid')
            return
        if self.mode == 'production':
            raise PaymentBoundaryError('webhook:production_activation_separately_approved')
        if self.mode != 'sandbox':
            raise PaymentBoundaryError('webhook:mode_not_allowlisted')
        if not SECRET_REF.fullmatch(self.secret_ref or ''):
            raise PaymentBoundaryError('webhook:secret_ref_required')
        if not re.fullmatch(r'approval-[a-f0-9]{16,64}', self.approval_receipt or ''):
            raise PaymentBoundaryError('webhook:approval_required')


class LocalFakePaymentProvider:
    """A credential-free, socket-free provider used only by tests and previews."""

    def __init__(self, activation: PaymentActivation):
        activation.validate()
        if not activation.enabled:
            raise PaymentBoundaryError('payment:disabled')
        self._states: dict[str, str] = {}

    @staticmethod
    def _id(prefix: str, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        return f'{prefix}_{hashlib.sha256(encoded).hexdigest()[:24]}'

    def charge(self, *, tenant_id: str, amount_minor: int, currency: str, replay_key: str):
        if not tenant_id or not replay_key or amount_minor < 1 or not re.fullmatch(r'[A-Z]{3}', currency):
            raise PaymentBoundaryError('payment:invalid_charge')
        payload = {
            'tenantId': tenant_id,
            'amountMinor': amount_minor,
            'currency': currency,
            'replayKey': replay_key,
        }
        payment_id = self._id('fakepay', payload)
        self._states.setdefault(payment_id, 'authorized')
        return {'paymentId': payment_id, 'status': self._states[payment_id], 'provider': 'local_fake'}

    def cancel(self, payment_id: str):
        state = self._states.get(payment_id)
        if state is None:
            raise PaymentBoundaryError('payment:not_found')
        if state == 'refunded':
            raise PaymentBoundaryError('payment:invalid_transition')
        self._states[payment_id] = 'cancelled'
        return {'paymentId': payment_id, 'status': 'cancelled'}

    def refund(self, payment_id: str):
        state = self._states.get(payment_id)
        if state is None:
            raise PaymentBoundaryError('payment:not_found')
        if state == 'cancelled':
            raise PaymentBoundaryError('payment:invalid_transition')
        self._states[payment_id] = 'refunded'
        return {'paymentId': payment_id, 'status': 'refunded'}


def verify_webhook(
    *,
    body: bytes,
    timestamp: str,
    signature: str,
    event_id: str,
    secret: bytes,
    replay_store: MutableSet[str],
    now: Callable[[], float] = time.time,
    max_age_seconds: int = 300,
) -> dict[str, Any]:
    if len(body) > 262_144:
        raise PaymentBoundaryError('webhook:body_too_large')
    if not EVENT_ID.fullmatch(event_id or ''):
        raise PaymentBoundaryError('webhook:invalid_event_id')
    try:
        issued = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise PaymentBoundaryError('webhook:invalid_timestamp') from exc
    if abs(int(now()) - issued) > max_age_seconds:
        raise PaymentBoundaryError('webhook:stale')
    expected = hmac.new(secret, timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ''):
        raise PaymentBoundaryError('webhook:invalid_signature')
    replay_key = f'{event_id}:{hashlib.sha256(body).hexdigest()}'
    if event_id in replay_store:
        if replay_key in replay_store:
            return {'eventId': event_id, 'replayed': True}
        raise PaymentBoundaryError('webhook:event_conflict')
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PaymentBoundaryError('webhook:invalid_json') from exc
    if not isinstance(payload, dict) or payload.get('type') not in {
        'payment.authorized', 'payment.cancelled', 'payment.refunded'
    }:
        raise PaymentBoundaryError('webhook:event_not_allowlisted')
    replay_store.add(event_id)
    replay_store.add(replay_key)
    return {'eventId': event_id, 'type': payload['type'], 'replayed': False}
