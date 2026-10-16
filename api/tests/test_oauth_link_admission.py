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


@pytest.mark.parametrize('local_verified', [True, False])
def test_unverified_provider_collision_never_links_or_issues_session(monkeypatch, local_verified):
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
                ident=GoogleIdentity('unlinked-sub', 'existing@example.com', False, '', ''),
                request=request,
                response=response,
            )
        )
    assert error.value.status_code == 401
    link.assert_not_called()
    assert not response.headers.get('set-cookie')
    assert audit.call_args.kwargs['action'] == 'auth.oauth_link_rejected'
