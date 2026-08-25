from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from api.main import app
from api.routes.site_content import get_site_content_service
from api.security.engagement import EngagementPolicyError


class CommunityService:
    def submit_community(self, **kwargs):
        return {'id': 'record-1234', 'moderationStatus': 'pending', **kwargs}


def principal():
    return SimpleNamespace(
        user_id=UUID('11111111-1111-4111-8111-111111111111'),
        authenticated_at=datetime.now(UTC),
        recently_authenticated=False,
    )


def test_community_route_binds_tenant_author_and_rate_limit(monkeypatch):
    app.dependency_overrides[get_site_content_service] = CommunityService
    monkeypatch.setattr('api.routes.engagement.require_authenticated_principal', lambda _request: principal())
    monkeypatch.setattr(
        'api.routes.engagement.rate_limit.incr_and_check_tenant_detailed',
        lambda *_args: (1, False, 0),
    )
    try:
        response = TestClient(app).post(
            '/api/engagement/community',
            headers={'X-Tenant-Id': 'site-a'},
            json={'title': 'Useful update', 'body': 'A sufficiently detailed community post.'},
        )
        assert response.status_code == 202
        assert response.json()['site_id'] == 'site-a'
        assert response.json()['author_ref'] == str(principal().user_id)

        monkeypatch.setattr(
            'api.routes.engagement.rate_limit.incr_and_check_tenant_detailed',
            lambda *_args: (11, True, 23),
        )
        rejected = TestClient(app).post(
            '/api/engagement/community',
            headers={'X-Tenant-Id': 'site-a'},
            json={'title': 'Useful update', 'body': 'A sufficiently detailed community post.'},
        )
        assert rejected.status_code == 429
        assert rejected.headers['Retry-After'] == '23'
    finally:
        app.dependency_overrides.clear()


def test_community_route_maps_policy_rejection(monkeypatch):
    class RejectingService:
        def submit_community(self, **_kwargs):
            raise EngagementPolicyError('body:active_content')

    app.dependency_overrides[get_site_content_service] = RejectingService
    monkeypatch.setattr('api.routes.engagement.require_authenticated_principal', lambda _request: principal())
    monkeypatch.setattr(
        'api.routes.engagement.rate_limit.incr_and_check_tenant_detailed',
        lambda *_args: (1, False, 0),
    )
    try:
        response = TestClient(app).post(
            '/api/engagement/community',
            headers={'X-Tenant-Id': 'site-a'},
            json={'title': 'Useful update', 'body': 'A sufficiently detailed community post.'},
        )
        assert response.status_code == 400
        assert response.json() == {'detail': 'body:active_content'}
    finally:
        app.dependency_overrides.clear()
