from uuid import uuid4
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from api.routes.auth import _navigation_permissions


def request(tenant=None):
    return Request(
        {'type': 'http', 'headers': [(b'x-tenant-id', tenant.encode())] if tenant else []}
    )


def test_legacy_client_receives_no_permission_claims(monkeypatch):
    lookup = Mock()
    monkeypatch.setattr('api.repositories.identity_admin.membership', lookup)
    assert _navigation_permissions(request(), uuid4()) == []
    lookup.assert_not_called()


@pytest.mark.parametrize(
    'member,permission',
    [
        (None, None),
        ({'role': 'viewer'}, 'media.read'),
        ({'role': 'editor'}, 'media.upload'),
        ({'role': 'unknown'}, None),
    ],
)
def test_projection_uses_current_tenant_membership(monkeypatch, member, permission):
    user = uuid4()
    lookup = Mock(return_value=member)
    monkeypatch.setattr('api.repositories.identity_admin.membership', lookup)
    result = _navigation_permissions(request('base2-obsidian'), user)
    lookup.assert_called_once_with(user_id=user, tenant_id='base2-obsidian')
    if permission:
        assert permission in result
        assert 'member.manage' not in result
    else:
        assert result == []


def test_lookup_failure_does_not_silently_claim_permissions(monkeypatch):
    monkeypatch.setattr(
        'api.repositories.identity_admin.membership', Mock(side_effect=RuntimeError('private'))
    )
    with pytest.raises(HTTPException) as error:
        _navigation_permissions(request('base2-obsidian'), uuid4())
    assert error.value.status_code == 503
    assert error.value.detail == 'Account permissions unavailable'
