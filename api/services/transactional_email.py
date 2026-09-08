from __future__ import annotations

import hashlib
import html
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
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


class SmtpEmailAdapter:
    """TLS-only production adapter with bounded network timeouts."""

    name = 'smtp'

    def __init__(self, *, host: str, port: int, username: str, password: str,
                 from_address: str, timeout: float = 10.0):
        if not host or any(value in host for value in ('\r', '\n', '/', ':')):
            raise ValueError('smtp_host_invalid')
        if port not in {465, 587}:
            raise ValueError('smtp_port_invalid')
        if '@' not in from_address or any(value in from_address for value in ('\r', '\n')):
            raise ValueError('smtp_from_invalid')
        if not username or not password or timeout <= 0 or timeout > 30:
            raise ValueError('smtp_configuration_invalid')
        self.host, self.port = host, port
        self.username, self.password = username, password
        self.from_address, self.timeout = from_address, timeout

    def send(self, message: RenderedEmail) -> AdapterResult:
        envelope = EmailMessage()
        envelope['From'], envelope['To'], envelope['Subject'] = (
            self.from_address, message.recipient, message.subject
        )
        envelope.set_content(message.text)
        if message.html:
            envelope.add_alternative(message.html, subtype='html')
        context = ssl.create_default_context()
        try:
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout,
                                      context=context) as client:
                    client.login(self.username, self.password)
                    client.send_message(envelope)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as client:
                    client.ehlo()
                    client.starttls(context=context)
                    client.ehlo()
                    client.login(self.username, self.password)
                    client.send_message(envelope)
        except smtplib.SMTPResponseException as exc:
            return AdapterResult('failed', retryable=400 <= exc.smtp_code < 500)
        except (OSError, smtplib.SMTPException):
            return AdapterResult('failed', retryable=True)
        return AdapterResult('sent')


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
