from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def recovery(monkeypatch):
    monkeypatch.setattr('api.routes.auth.settings.FRONTEND_URL', 'https://example.test')
    monkeypatch.setattr(
        'api.security.rate_limit.incr_and_check_detailed', lambda *args: (1, False, 0)
    )
    monkeypatch.setattr(
        'api.security.rate_limit.incr_and_check_identifier_detailed', lambda *args: (1, False, 0)
    )
    issue = Mock()
    monkeypatch.setattr('api.auth.service.issue_verify_email', issue)
    return TestClient(app), issue


def test_recovery_uses_trusted_origin_and_neutral_response(recovery):
    client, issue = recovery
    result = client.post(
        '/api/auth/resend-verification',
        json={'email': 'TEST@example.test'},
        headers={'Host': 'attacker.test', 'X-Forwarded-Proto': 'http'},
    )
    assert result.status_code == 202
    assert 'requested' in result.json()['detail']
    issue.assert_called_once_with(
        email='test@example.test', host='example.test', proto='https', raise_on_failure=True
    )


@pytest.mark.parametrize('scope', ['incr_and_check_detailed', 'incr_and_check_identifier_detailed'])
def test_recovery_enforces_both_limits(recovery, monkeypatch, scope):
    client, issue = recovery
    monkeypatch.setattr(f'api.security.rate_limit.{scope}', lambda *args: (2, True, 45))
    result = client.post('/api/auth/resend-verification', json={'email': 'test@example.test'})
    assert result.status_code == 429
    assert result.headers['retry-after'] == '45'
    issue.assert_not_called()


def test_unavailable_limiter_fails_closed(recovery, monkeypatch):
    client, issue = recovery
    monkeypatch.setattr(
        'api.security.rate_limit.incr_and_check_detailed', Mock(side_effect=RuntimeError('private'))
    )
    result = client.post('/api/auth/resend-verification', json={'email': 'test@example.test'})
    assert result.status_code == 503
    assert 'private' not in result.text
    issue.assert_not_called()


def test_missing_trusted_origin_fails_closed(recovery, monkeypatch):
    client, issue = recovery
    monkeypatch.setattr('api.routes.auth.settings.FRONTEND_URL', '')
    assert (
        client.post(
            '/api/auth/resend-verification', json={'email': 'test@example.test'}
        ).status_code
        == 503
    )
    issue.assert_not_called()


def test_mail_failure_is_logged_without_exposing_account_or_secret(recovery, caplog):
    client, issue = recovery
    baseline = client.post('/api/auth/resend-verification', json={'email': 'test@example.test'})
    issue.side_effect = RuntimeError('private-token-and-recipient')
    failed = client.post('/api/auth/resend-verification', json={'email': 'test@example.test'})
    assert failed.status_code == baseline.status_code == 202
    assert failed.json() == baseline.json()
    assert 'verification_recovery_enqueue_failed' in caplog.text
    assert 'private-token-and-recipient' not in caplog.text


@pytest.mark.parametrize('email', ['', 'invalid', 'a' * 255 + '@example.test'])
def test_invalid_email_never_enqueues(recovery, email):
    client, issue = recovery
    assert client.post('/api/auth/resend-verification', json={'email': email}).status_code == 422
    issue.assert_not_called()


@pytest.mark.parametrize('verified', [None, True])
def test_service_unknown_and_verified_users_do_not_create_tokens_or_mail(monkeypatch, verified):
    from types import SimpleNamespace
    from api.auth import service

    user = None if verified is None else SimpleNamespace(is_email_verified=True)
    monkeypatch.setattr(service.repo, 'get_user_by_email', lambda email: user)
    create = Mock()
    enqueue = Mock()
    monkeypatch.setattr(service.repo, 'create_one_time_token', create)
    monkeypatch.setattr('api.services.email_service.queue_email', enqueue)
    service.issue_verify_email(
        email='fixture@example.test', host='example.test', proto='https', raise_on_failure=True
    )
    create.assert_not_called()
    enqueue.assert_not_called()


@pytest.mark.parametrize('failure', ['email_budget_exhausted', 'adapter-private-detail'])
def test_service_surfaces_sanitized_enqueue_failure(monkeypatch, failure):
    from types import SimpleNamespace
    from api.auth import service

    monkeypatch.setattr(
        service.repo,
        'get_user_by_email',
        lambda email: SimpleNamespace(id='fixture-id', email=email, is_email_verified=False),
    )
    create = Mock()
    monkeypatch.setattr(service.repo, 'create_one_time_token', create)
    monkeypatch.setattr(
        'api.services.email_service.queue_email', Mock(side_effect=RuntimeError(failure))
    )
    with pytest.raises(RuntimeError, match='^verification_enqueue_failed$'):
        service.issue_verify_email(
            email='fixture@example.test', host='example.test', proto='https', raise_on_failure=True
        )
    create.assert_called_once()
    assert create.call_args.kwargs['token_type'] == 'verify_email'
