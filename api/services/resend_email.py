"""Resend transport boundary; activation and durable retry policy are separate.

`sent` means provider acceptance, never confirmed inbox delivery. Until durable
retry-age/cap enforcement exists, all failures require reconciliation, not retry.
"""

import hashlib
import math
import os
import re

import httpx

from api.services.transactional_email import AdapterResult, RenderedEmail
from api.services.email_send_budget import reserve_send


def _mailbox(value: str) -> bool:
    return bool(
        re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}", value)
    )


class ResendEmailAdapter:
    name = 'resend'

    def __init__(
        self,
        *,
        api_key: str,
        from_address: str,
        allowed_recipients: set[str],
        budget_file: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        recipients = {value.strip().lower() for value in allowed_recipients}
        if (
            not re.fullmatch(r'[A-Za-z0-9_-]+', api_key)
            or not os.path.isabs(budget_file)
            or not _mailbox(from_address)
            or not recipients
            or not all(_mailbox(value) for value in recipients)
            or not math.isfinite(timeout)
            or not 0 < timeout <= 30
        ):
            raise ValueError('resend_configuration_invalid')
        self._api_key = api_key
        self._from = from_address
        self._recipients = frozenset(recipients)
        self._timeout = timeout
        self._transport = transport
        self._budget_file = budget_file

    def send(self, message: RenderedEmail) -> AdapterResult:
        recipient = message.recipient.strip().lower()
        if recipient not in self._recipients:
            return AdapterResult('suppressed')
        if not message.delivery_key:
            return AdapterResult('failed', failure_code='resend_delivery_key_missing')
        key = 'base2-' + hashlib.sha256(message.delivery_key.encode()).hexdigest()
        reserve_send(self._budget_file, message.delivery_key)
        try:
            with httpx.Client(
                timeout=self._timeout,
                verify=True,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as client:
                response = client.post(
                    'https://api.resend.com/emails',
                    headers={'Authorization': f'Bearer {self._api_key}', 'Idempotency-Key': key},
                    json={
                        'from': self._from,
                        'to': [recipient],
                        'subject': message.subject,
                        'text': message.text,
                        'html': message.html,
                    },
                )
            if response.status_code != 200:
                status = response.status_code
                code = (
                    'resend_auth_rejected'
                    if status in {401, 403}
                    else 'resend_rate_limited'
                    if status == 429
                    else 'resend_provider_unavailable'
                    if status >= 500
                    else 'resend_request_rejected'
                    if 400 <= status < 500
                    else 'resend_unexpected_response'
                )
                return AdapterResult('failed', failure_code=code)
            payload = response.json()
            identity = payload.get('id') if isinstance(payload, dict) else None
            if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', identity):
                return AdapterResult('failed', failure_code='resend_unexpected_response')
            return AdapterResult('sent', identity)
        except (httpx.HTTPError, ValueError):
            # Provider bodies and exceptions may contain credentials or reset links.
            return AdapterResult('failed', failure_code='resend_delivery_uncertain')
