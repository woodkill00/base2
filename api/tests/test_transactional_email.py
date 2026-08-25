from datetime import datetime, timezone
from uuid import uuid4

import pytest

from api.services.email_service import EmailOutboxRow, _configured_adapter, safe_outbox_diagnostic
from api.services.transactional_email import (
    AdapterResult,
    DisabledEmailAdapter,
    LocalFakeEmailAdapter,
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
    monkeypatch.setenv('BASE2_EMAIL_ADAPTER', 'smtp')
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
