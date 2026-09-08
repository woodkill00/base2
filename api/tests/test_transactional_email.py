from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from api.services import email_service
from api.services.email_service import EmailOutboxRow, _configured_adapter, safe_outbox_diagnostic
from api.services.transactional_email import (
    AdapterResult,
    DisabledEmailAdapter,
    LocalFakeEmailAdapter,
    SmtpEmailAdapter,
    deliver_email,
    recipient_digest,
    render_email,
)


def test_all_transactional_templates_render_safe_text_and_html():
    contexts = {
        'verification': {'url': 'https://example.test/verify?t=redacted'},
        'password_reset': {'url': 'https://example.test/reset?t=redacted'},
        'contact_receipt': {'privacy_url': 'https://example.test/privacy'},
        'invitation': {'url': 'https://example.test/invite?t=redacted'},
    }
    for kind, context in contexts.items():
        message = render_email(kind, 'Person@Example.Test', {'name': '<Owner>', **context})
        assert message.recipient == 'person@example.test'
        assert '<Owner>' in message.text
        assert '&lt;Owner&gt;' in message.html
        assert '\r' not in message.subject and '\n' not in message.subject


def test_disabled_is_default_safe_behavior_and_local_fake_never_uses_network():
    message = render_email(
        'verification', 'person@example.test', {'url': 'https://example.test/verify'}
    )
    assert deliver_email(message, DisabledEmailAdapter()).status == 'disabled'
    fake = LocalFakeEmailAdapter()
    result = deliver_email(message, fake)
    assert result.status == 'sent'
    assert result.message_id.startswith('fake-')
    assert fake.messages == [message]


def test_retry_exhaustion_bounce_suppression_and_privacy_safe_diagnostics():
    message = render_email(
        'password_reset', 'secret@example.test', {'url': 'https://example.test/reset'}
    )
    retry = LocalFakeEmailAdapter(AdapterResult('failed', retryable=True))
    assert deliver_email(message, retry, attempt=1).status == 'retry'
    assert deliver_email(message, retry, attempt=3).status == 'dead_letter'
    bounce = LocalFakeEmailAdapter(AdapterResult('bounced'))
    assert deliver_email(message, bounce).status == 'suppressed'
    suppressed = deliver_email(
        message,
        LocalFakeEmailAdapter(),
        suppressed_recipient_digests={recipient_digest(message.recipient)},
    )
    assert suppressed.status == 'suppressed'
    assert 'secret@example.test' not in str(suppressed.diagnostic)


def test_hostile_addresses_urls_and_unknown_templates_fail_closed():
    for recipient in ('missing-at', 'a@example.test\nBcc: attacker@example.test'):
        try:
            render_email('verification', recipient, {'url': 'https://example.test'})
        except ValueError:
            pass
        else:
            raise AssertionError('hostile recipient accepted')
    for url in ('javascript:alert(1)', 'http://example.test/reset'):
        try:
            render_email('password_reset', 'a@example.test', {'url': url})
        except ValueError:
            pass
        else:
            raise AssertionError('unsafe URL accepted')


def test_runtime_adapter_allowlist_and_operator_diagnostic_are_safe(monkeypatch):
    monkeypatch.delenv('BASE2_EMAIL_ADAPTER', raising=False)
    assert _configured_adapter().name == 'disabled'
    monkeypatch.setenv('BASE2_EMAIL_ADAPTER', 'unknown')
    with pytest.raises(RuntimeError, match='email_adapter_not_allowed'):
        _configured_adapter()
    now = datetime.now(timezone.utc)
    row = EmailOutboxRow(
        uuid4(),
        'private@example.test',
        'subject',
        'secret body',
        '<p>secret</p>',
        'disabled',
        'disabled',
        '',
        'delivery_disabled',
        now,
        None,
    )
    diagnostic = safe_outbox_diagnostic(row)
    assert diagnostic['status'] == 'disabled'
    assert diagnostic['hasError'] is True
    assert 'private@example.test' not in str(diagnostic)
    assert 'secret body' not in str(diagnostic)


def test_smtp_adapter_requires_tls_port_and_sends_without_exposing_credentials(monkeypatch):
    calls = []

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            calls.append(('connect', host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def ehlo(self):
            calls.append(('ehlo',))

        def starttls(self, *, context):
            assert context is not None
            calls.append(('starttls',))

        def login(self, username, password):
            assert username == 'smtp-user' and password == 'smtp-password'
            calls.append(('login',))

        def send_message(self, message):
            assert message['To'] == 'person@example.test'
            calls.append(('send',))

    monkeypatch.setattr('api.services.transactional_email.smtplib.SMTP', FakeSmtp)
    adapter = SmtpEmailAdapter(
        host='smtp.example.test', port=587, username='smtp-user',
        password='smtp-password', from_address='no-reply@example.test', timeout=5,
    )
    message = render_email(
        'verification', 'person@example.test', {'url': 'https://example.test/verify'}
    )
    assert deliver_email(message, adapter).status == 'sent'
    assert ('starttls',) in calls and ('send',) in calls
    with pytest.raises(ValueError, match='smtp_port_invalid'):
        SmtpEmailAdapter(
            host='smtp.example.test', port=25, username='user', password='password',
            from_address='no-reply@example.test',
        )


def test_outbox_retry_is_durable_and_becomes_dead_letter_after_bound(monkeypatch):
    row = EmailOutboxRow(
        uuid4(), 'private@example.test', 'subject', 'body', '', 'sending',
        'worker_claim', '', 'delivery_retry:2', datetime.now(timezone.utc), None,
    )
    monkeypatch.setattr(email_service, 'claim_outbox_email', lambda _outbox_id: row)
    monkeypatch.setattr(
        email_service, '_configured_adapter',
        lambda: LocalFakeEmailAdapter(AdapterResult('failed', retryable=True)),
    )
    mark = MagicMock()
    monkeypatch.setattr(email_service, 'mark_outbox_status', mark)
    email_service.process_outbox_email(outbox_id=row.id)
    assert mark.call_args.kwargs['status'] == 'dead_letter'
    assert mark.call_args.kwargs['error'] == 'delivery_dead_letter'
