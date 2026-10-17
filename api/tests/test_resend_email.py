import json

import httpx
import pytest

from api.services.resend_email import ResendEmailAdapter
from api.services.transactional_email import RenderedEmail


MESSAGE = RenderedEmail(
    'verification', 'owner@example.com', 'Verify', 'private', '<p>private</p>', 'outbox-1'
)


@pytest.fixture(autouse=True)
def mock_budget(monkeypatch):
    monkeypatch.setattr('api.services.resend_email.reserve_send', lambda *args: None)


def adapter(handler, **overrides):
    options = dict(
        api_key='re_test_only',
        budget_file='/private/test-budget.json',
        from_address='test@example.com',
        allowed_recipients={'owner@example.com'},
        transport=httpx.MockTransport(handler),
    )
    options.update(overrides)
    return ResendEmailAdapter(**options)


def test_acceptance_uses_fixed_endpoint_and_stable_key():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={'id': 'email-123'})

    mailer = adapter(handle)
    assert mailer.send(MESSAGE).message_id == 'email-123'
    assert mailer.send(MESSAGE).status == 'sent'
    assert len(requests) == 2
    assert str(requests[0].url) == 'https://api.resend.com/emails'
    assert requests[0].headers['Idempotency-Key'] == requests[1].headers['Idempotency-Key']
    assert json.loads(requests[0].content)['to'] == ['owner@example.com']


@pytest.mark.parametrize('status', [301, 400, 401, 403, 409, 422, 429, 500, 503])
def test_errors_are_sanitized_and_not_automatically_retried(status):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            status,
            json={'message': 'secret-provider-detail'},
            headers={'Location': 'https://evil.example'},
        )

    result = adapter(handle).send(MESSAGE)
    assert result.status == 'failed'
    assert result.retryable is False
    assert result.message_id == ''
    assert len(calls) == 1
    assert 'secret' not in repr(result)
    assert result.failure_code.startswith('resend_')


@pytest.mark.parametrize('payload', [[], {}, {'id': ''}, {'id': 'a\nsecret'}, {'id': 1}])
def test_malformed_acceptance_requires_reconciliation(payload):
    assert adapter(lambda _: httpx.Response(200, json=payload)).send(MESSAGE).status == 'failed'


def test_timeout_does_not_risk_automatic_duplicate_send():
    def handle(request):
        raise httpx.ReadTimeout('secret', request=request)

    result = adapter(handle).send(MESSAGE)
    assert result.status == 'failed' and not result.retryable


def test_budget_failure_prevents_network(monkeypatch):
    def fail(*args):
        raise RuntimeError('email_budget_exhausted')

    monkeypatch.setattr('api.services.resend_email.reserve_send', fail)
    with pytest.raises(RuntimeError, match='email_budget_exhausted'):
        adapter(lambda _: pytest.fail('must not send')).send(MESSAGE)


def test_non_json_acceptance_does_not_claim_delivery():
    result = adapter(lambda _: httpx.Response(200, text='not JSON')).send(MESSAGE)
    assert result.status == 'failed' and not result.retryable


def test_transport_disables_redirects_environment_proxies_and_insecure_tls(monkeypatch):
    original = httpx.Client
    options = []

    def client(**kwargs):
        options.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr('api.services.resend_email.httpx.Client', client)
    adapter(lambda _: httpx.Response(200, json={'id': 'email-123'})).send(MESSAGE)
    assert options[0]['verify'] is True
    assert options[0]['follow_redirects'] is False
    assert options[0]['trust_env'] is False
    assert options[0]['timeout'] == 10


def test_runtime_secret_configuration_and_permissions(tmp_path, monkeypatch):
    from api.services.email_service import _configured_adapter

    key = tmp_path / 'key'
    key.write_text('re_test_only')
    key.chmod(0o600)
    monkeypatch.setenv('BASE2_EMAIL_ADAPTER', 'resend')
    monkeypatch.setenv('BASE2_EMAIL_RESEND_API_KEY_FILE', str(key))
    monkeypatch.setenv('BASE2_EMAIL_FROM_ADDRESS', 'sender@example.com')
    monkeypatch.setenv('BASE2_EMAIL_ALLOWED_RECIPIENTS', 'owner@example.com')
    monkeypatch.setenv('BASE2_EMAIL_BUDGET_FILE', str(tmp_path / 'budget'))
    assert _configured_adapter().name == 'resend'
    key.chmod(0o644)
    with pytest.raises(RuntimeError, match='email_secret_file_permissions'):
        _configured_adapter()
    key.chmod(0o600)
    monkeypatch.setenv('BASE2_EMAIL_ALLOWED_RECIPIENTS', '')
    with pytest.raises(RuntimeError, match='email_resend_configuration_invalid'):
        _configured_adapter()


def test_denied_recipient_and_missing_key_never_reach_network():
    def forbidden(_):
        pytest.fail('network must not be used')

    assert (
        adapter(forbidden, allowed_recipients={'other@example.com'}).send(MESSAGE).status
        == 'suppressed'
    )
    message = RenderedEmail('verification', MESSAGE.recipient, 'subject', 'text', '')
    assert adapter(forbidden).send(message).status == 'failed'


@pytest.mark.parametrize(
    'overrides',
    [
        {'api_key': ''},
        {'api_key': 'secret\nvalue'},
        {'allowed_recipients': set()},
        {'from_address': 'bad\n@example.com'},
        {'timeout': float('nan')},
        {'timeout': 0},
        {'timeout': 31},
        {'allowed_recipients': {'a@example.com,b@example.com'}},
    ],
)
def test_invalid_configuration_is_rejected(overrides):
    with pytest.raises(ValueError, match='resend_configuration_invalid'):
        adapter(lambda _: pytest.fail('network must not be used'), **overrides)
