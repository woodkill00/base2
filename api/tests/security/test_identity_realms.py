from uuid import UUID
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from api.security.request_auth import require_authenticated_principal, require_authenticated_user


USER_ID = UUID('00000000-0000-0000-0000-000000000321')


class Request:
    headers = {'authorization': 'Bearer fixture-token'}


def test_public_token_role_tenant_and_permission_claims_never_become_authority(monkeypatch):
    monkeypatch.setattr(
        'api.auth.tokens.decode_access_token',
        lambda token: {
            'sub': str(USER_ID),
            'role': 'owner',
            'permissions': ['*'],
            'tenant_id': 'other-tenant',
            'organization_id': 'other-org',
        },
    )

    principal = require_authenticated_user(Request())

    assert principal == USER_ID
    assert isinstance(principal, UUID)
    assert not hasattr(principal, 'role')


@pytest.mark.parametrize('subject', (None, '', '1', 'not-a-uuid'))
def test_non_public_account_subjects_fail_closed(monkeypatch, subject):
    monkeypatch.setattr('api.auth.tokens.decode_access_token', lambda token: {'sub': subject})
    with pytest.raises(HTTPException) as exc:
        require_authenticated_user(Request())
    assert exc.value.status_code == 401
    assert exc.value.detail == 'not_authenticated'


def test_sensitive_principal_binds_server_validated_issue_time(monkeypatch):
    issued_at = int(datetime.now(timezone.utc).timestamp())
    monkeypatch.setattr(
        'api.auth.tokens.decode_access_token',
        lambda token: {
            'sub': str(USER_ID), 'iat': issued_at, 'role': 'owner', 'reauth': True
        },
    )
    principal = require_authenticated_principal(Request())
    assert principal.user_id == USER_ID
    assert int(principal.authenticated_at.timestamp()) == issued_at
    assert principal.recently_authenticated is True


def test_refreshed_principal_cannot_claim_recent_reauthentication(monkeypatch):
    issued_at = int(datetime.now(timezone.utc).timestamp())
    monkeypatch.setattr(
        'api.auth.tokens.decode_access_token',
        lambda token: {'sub': str(USER_ID), 'iat': issued_at, 'reauth': False},
    )
    principal = require_authenticated_principal(Request())
    assert principal.user_id == USER_ID
    assert principal.recently_authenticated is False


@pytest.mark.parametrize('issued_at', (None, '', 'invalid'))
def test_sensitive_principal_rejects_missing_or_invalid_issue_time(monkeypatch, issued_at):
    monkeypatch.setattr(
        'api.auth.tokens.decode_access_token',
        lambda token: {'sub': str(USER_ID), 'iat': issued_at},
    )
    with pytest.raises(HTTPException) as exc:
        require_authenticated_principal(Request())
    assert exc.value.status_code == 401
