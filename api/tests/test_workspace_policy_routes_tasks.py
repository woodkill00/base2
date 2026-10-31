"""HTTP adapters and trusted task dispatch, independent of real PostgreSQL proof."""

from types import SimpleNamespace
from uuid import UUID
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from api.main import app
from api import tasks
from api.routes import content_workspace, settings as routes

ACTOR = UUID(int=11)
RECORD = UUID(int=33)


@pytest.mark.parametrize('adopt', [False, True])
@pytest.mark.parametrize(
    'error,code',
    [
        (None, 200),
        (PermissionError('private'), 404),
        (ValueError('content_not_found'), 404),
        (ValueError('content_version_conflict'), 409),
        (ValueError('content_review_no_independent_reviewer'), 422),
        (RuntimeError('private-db-detail'), 503),
    ],
)
def test_review_http_adapter_authorizes_exact_action_and_closes_errors(
    monkeypatch, adopt, error, code
):
    seen = []

    def scope(_request, permission):
        seen.append(permission)
        return SimpleNamespace(user_id=ACTOR), 'site-a'

    monkeypatch.setattr(content_workspace, '_authorized_scope', scope)

    def action(**kwargs):
        assert kwargs == {
            'site_id': 'site-a',
            'type_key': 'article',
            'record_id': RECORD,
            'user_id': ACTOR,
            'expected_version': 2,
            'adopt': adopt,
        }
        if error:
            raise error
        return {
            'record_id': str(RECORD),
            'version': 3 if adopt else 2,
            'state': 'draft' if adopt else 'in_review',
            'review_status': 'draft' if adopt else 'approved',
        }

    monkeypatch.setattr('api.repositories.workspace_policy.review_action', action)
    body = {'expected_version': 2}
    if adopt:
        body['adopt_snapshot'] = True
    result = TestClient(app).post(
        f'/api/content/v1/types/article/records/{RECORD}/'
        + ('review-subject' if adopt else 'review-approval'),
        json=body,
    )
    assert result.status_code == code
    assert seen == ['content-workspace.write' if adopt else 'content-workspace.publish']
    assert (
        'private-db-detail' not in result.text
        and result.headers['cache-control'] == 'private, no-store'
    )


def test_policy_scope_checks_deployment_and_server_tenant(monkeypatch):
    principal = SimpleNamespace(user_id=ACTOR)
    monkeypatch.setattr(routes, '_principal_and_tenant', lambda _: (principal, 'site-a'))
    monkeypatch.setattr(routes, 'SITE_MANIFEST', {'modules': []})
    with pytest.raises(HTTPException) as error:
        routes._policy_scope(object())
    assert error.value.status_code == 404
    monkeypatch.setattr(
        routes,
        'SITE_MANIFEST',
        {'modules': [{'id': name, 'enabled': True} for name in ('accounts', 'content-workspace')]},
    )
    assert routes._policy_scope(object()) == (principal, 'site-a')


@pytest.mark.parametrize(
    'method,error,code',
    [
        ('get', PermissionError('private'), 404),
        ('put', ValueError('storage_transport_unverified'), 422),
        ('put', RuntimeError('private-detail'), 503),
        ('put', None, 200),
    ],
)
def test_policy_http_error_and_success_envelopes(monkeypatch, method, error, code):
    monkeypatch.setattr(
        routes, '_policy_scope', lambda _: (SimpleNamespace(user_id=ACTOR), 'site-a')
    )

    def result(**_):
        if error:
            raise error
        return {'schema_version': 1, 'version': 2}

    monkeypatch.setattr(
        routes.workspace_policy, 'get_policy' if method == 'get' else 'update_policy', result
    )
    client = TestClient(app)
    response = (
        client.get('/api/settings/workspace-policy')
        if method == 'get'
        else client.put(
            '/api/settings/workspace-policy',
            json={'expected_version': 1, 'require_review': True, 'public_access': 'members_only'},
        )
    )
    assert response.status_code == code and 'private-detail' not in response.text


@pytest.mark.parametrize('enabled', [False, True])
def test_review_notification_task_only_uses_trusted_deployment_site(monkeypatch, enabled):
    import api.settings

    manifest = {
        'siteId': 'trusted-site',
        'modules': [{'id': name, 'enabled': enabled} for name in ('accounts', 'content-workspace')],
    }
    monkeypatch.setattr(api.settings, 'SITE_MANIFEST', manifest)
    calls = []
    monkeypatch.setattr(tasks, '_tenant_serving', lambda site: calls.append(site) or True)
    monkeypatch.setattr(
        'api.services.workspace_review_notifications.process_review_notifications',
        lambda **kwargs: calls.append(kwargs) or {'adapter': 'local_test'},
    )
    if enabled:
        assert tasks.process_workspace_review_notifications() == {'adapter': 'local_test'}
        assert calls == ['trusted-site', {'site_id': 'trusted-site'}]
    else:
        assert tasks.process_workspace_review_notifications() == {
            'adapter': 'local_test',
            'status': 'capability_disabled',
        }
        assert calls == []
    monkeypatch.setattr(tasks, 'SITE_MANIFEST', {'modules': []})
    with pytest.raises(ValueError, match='content_capability_disabled'):
        tasks._require_workspace_capability()


def test_review_notification_task_refuses_inactive_deployment(monkeypatch):
    import api.settings

    monkeypatch.setattr(
        api.settings,
        'SITE_MANIFEST',
        {
            'siteId': 'trusted-site',
            'modules': [
                {'id': name, 'enabled': True} for name in ('accounts', 'content-workspace')
            ],
        },
    )
    monkeypatch.setattr(tasks, '_tenant_serving', lambda _: False)
    monkeypatch.setattr(
        'api.services.workspace_review_notifications.process_review_notifications',
        lambda **_: pytest.fail('inactive tenant delivered'),
    )
    assert tasks.process_workspace_review_notifications() == {
        'adapter': 'local_test',
        'status': 'tenant_not_serving',
    }
