"""Local account verification cannot vouch for a new external identity."""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException, Request, Response

from api.auth import repo
from api.routes.auth import complete_google_oauth_identity
from api.services.oauth_google import GoogleIdentity


@pytest.mark.parametrize('provider_verified', [True, False])
@pytest.mark.parametrize('local_verified', [True, False])
def test_unverified_provider_collision_never_links_or_issues_session(
    monkeypatch, local_verified, provider_verified
):
    monkeypatch.setattr(repo, 'find_oauth_account', lambda **kwargs: None)
    monkeypatch.setattr(
        repo,
        'get_user_by_email',
        lambda email: SimpleNamespace(
            id=UUID(int=9),
            is_email_verified=local_verified,
            is_active=True,
        ),
    )
    link = MagicMock()
    monkeypatch.setattr(repo, 'create_oauth_account', link)
    audit = MagicMock()
    monkeypatch.setattr(repo, 'insert_audit_event', audit)
    request = Request({'type': 'http', 'headers': [], 'client': ('127.0.0.1', 1)})
    response = Response()
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            complete_google_oauth_identity(
                ident=GoogleIdentity(
                    'unlinked-sub', 'existing@example.com', provider_verified, '', ''
                ),
                request=request,
                response=response,
            )
        )
    assert error.value.status_code == 401
    link.assert_not_called()
    assert not response.headers.get('set-cookie')
    assert audit.call_args.kwargs['action'] == 'auth.oauth_link_rejected'


@pytest.mark.parametrize(
    'email,verified,domain,expected',
    [
        ('user@gmail.com', True, '', True),
        ('user@GMAIL.COM', True, '', True),
        ('user@gmail.com.attacker.test', True, '', False),
        ('user@example.com', True, '', False),
        ('user@example.com', True, 'example.com', True),
        ('user@gmail.com', False, '', False),
        ('user@example.com', False, 'example.com', False),
    ],
)
def test_email_authority_requires_google_owned_mailbox(email, verified, domain, expected):
    assert (
        GoogleIdentity('sub', email, verified, '', '', domain).email_link_authoritative is expected
    )


@pytest.mark.parametrize('domain', ['example.com', '', None, {}, 'bad domain', 'bad/domain'])
def test_hosted_domain_is_only_taken_from_verified_claims(monkeypatch, domain):
    from google.oauth2 import id_token
    from api.services.oauth_google import verify_google_id_token

    verifier = MagicMock(
        return_value={
            'sub': 'subject',
            'email': 'user@example.com',
            'email_verified': True,
            'hd': domain,
        }
    )
    monkeypatch.setattr(id_token, 'verify_oauth2_token', verifier)
    if domain in ('example.com', ''):
        result = verify_google_id_token(id_token='synthetic', audience='test-client')
        assert result.hosted_domain == domain
        assert verifier.call_args.args[2] == 'test-client'
    else:
        with pytest.raises(ValueError, match='invalid_token'):
            verify_google_id_token(id_token='synthetic', audience='test-client')
