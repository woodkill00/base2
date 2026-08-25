from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.parse import urlparse

KINDS = {'verification', 'password_reset', 'contact_receipt', 'invitation'}


@dataclass(frozen=True)
class RenderedEmail:
    kind: str
    recipient: str
    subject: str
    text: str
    html: str


@dataclass(frozen=True)
class AdapterResult:
    status: str
    message_id: str = ''
    retryable: bool = False


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    provider: str
    message_id: str
    diagnostic: Mapping[str, object]


class EmailAdapter(Protocol):
    name: str

    def send(self, message: RenderedEmail) -> AdapterResult: ...


def recipient_digest(recipient: str) -> str:
    return hashlib.sha256(recipient.strip().lower().encode()).hexdigest()[:16]


def _safe_url(value: object) -> str:
    url = str(value or '')
    parsed = urlparse(url)
    if parsed.scheme not in {'https', 'http'} or not parsed.netloc or '\r' in url or '\n' in url:
        raise ValueError('email_url_invalid')
    if parsed.scheme == 'http' and parsed.hostname not in {'localhost', '127.0.0.1'}:
        raise ValueError('email_url_insecure')
    return url


def render_email(kind: str, recipient: str, context: Mapping[str, object]) -> RenderedEmail:
    if kind not in KINDS:
        raise ValueError('email_kind_unknown')
    clean_recipient = recipient.strip().lower()
    if '@' not in clean_recipient or any(value in clean_recipient for value in ('\r', '\n')):
        raise ValueError('email_recipient_invalid')
    name = str(context.get('name') or 'there').strip()[:120]
    escaped_name = html.escape(name)
    if kind == 'verification':
        subject, action, url = 'Verify your email', 'Verify email', _safe_url(context.get('url'))
    elif kind == 'password_reset':
        subject, action, url = 'Reset your password', 'Reset password', _safe_url(context.get('url'))
    elif kind == 'invitation':
        subject, action, url = 'You are invited', 'Review invitation', _safe_url(context.get('url'))
    else:
        subject, action, url = 'We received your message', 'View privacy information', _safe_url(
            context.get('privacy_url')
        )
    text = f'Hello {name},\n\n{action}: {url}\n\nIf you did not expect this message, ignore it.'
    body = (
        f'<p>Hello {escaped_name},</p><p><a href="{html.escape(url, quote=True)}">'
        f'{html.escape(action)}</a></p><p>If you did not expect this message, ignore it.</p>'
    )
    return RenderedEmail(kind, clean_recipient, subject, text, body)


class DisabledEmailAdapter:
    name = 'disabled'

    def send(self, message: RenderedEmail) -> AdapterResult:
        return AdapterResult('disabled')


class LocalFakeEmailAdapter:
    name = 'local_fake'

    def __init__(self, outcome: AdapterResult | None = None):
        self.outcome = outcome
        self.messages: list[RenderedEmail] = []

    def send(self, message: RenderedEmail) -> AdapterResult:
        self.messages.append(message)
        return self.outcome or AdapterResult(
            'sent', f'fake-{recipient_digest(message.recipient)}-{message.kind}'
        )


def deliver_email(
    message: RenderedEmail,
    adapter: EmailAdapter,
    *,
    attempt: int = 1,
    max_attempts: int = 3,
    suppressed_recipient_digests: set[str] | None = None,
) -> DeliveryResult:
    digest = recipient_digest(message.recipient)
    diagnostic = {'kind': message.kind, 'recipientDigest': digest, 'attempt': attempt}
    if digest in (suppressed_recipient_digests or set()):
        return DeliveryResult('suppressed', adapter.name, '', diagnostic)
    result = adapter.send(message)
    status = result.status
    if result.retryable:
        status = 'retry' if attempt < max_attempts else 'dead_letter'
    if status == 'bounced':
        status = 'suppressed'
    if status not in {'sent', 'disabled', 'suppressed', 'retry', 'dead_letter'}:
        status = 'dead_letter'
    return DeliveryResult(status, adapter.name, result.message_id, diagnostic)
