from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from api.main import app
from api.routes.site_content import get_site_content_service


NOW = datetime(2026, 8, 25, tzinfo=UTC)
CONTENT_ID = UUID('11111111-1111-4111-8111-111111111111')


class FakeSiteContentService:
    def __init__(self):
        self.form_calls = 0

    def list_content(self, *, site_id, limit, cursor):
        return {
            'items': [
                {
                    'id': CONTENT_ID,
                    'contentType': 'page',
                    'slug': 'about',
                    'title': 'About',
                    'excerpt': 'Public',
                    'body': 'Body',
                    'metadata': {},
                    'publishedAt': NOW,
                    'updatedAt': NOW,
                }
            ],
            'nextCursor': None,
        }

    def get_content(self, *, site_id, content_type, slug):
        if slug == 'missing':
            return None
        return self.list_content(site_id=site_id, limit=1, cursor=None)['items'][0]

    def get_media(self, *, site_id, asset_id):
        return None

    def search(self, *, site_id, query, limit, cursor):
        return {'items': [], 'nextCursor': None, 'freshThrough': NOW}

    def submit_form(self, *, site_id, form_key, replay_key, payload, consent, request_id):
        self.form_calls += 1
        return {
            'id': UUID('22222222-2222-4222-8222-222222222222'),
            'status': 'queued',
            'replayed': self.form_calls > 1,
            'receivedAt': NOW,
        }


def test_openapi_declares_public_content_media_form_and_search_contracts():
    schema = app.openapi()
    for path in (
        '/api/content',
        '/api/content/{content_type}/{slug}',
        '/api/media/{asset_id}',
        '/api/forms/{form_key}',
        '/api/search',
    ):
        assert path in schema['paths']
    assert schema['paths']['/api/forms/{form_key}']['post']['responses']['202']


def test_tenant_policy_pagination_not_found_and_search_mapping():
    fake = FakeSiteContentService()
    app.dependency_overrides[get_site_content_service] = lambda: fake
    try:
        client = TestClient(app)
        assert client.get('/api/content').status_code == 400
        response = client.get('/api/content?limit=25', headers={'X-Tenant-Id': 'site-a'})
        assert response.status_code == 200
        assert response.json()['items'][0]['slug'] == 'about'
        assert (
            client.get('/api/content?limit=101', headers={'X-Tenant-Id': 'site-a'}).status_code
            == 422
        )
        assert (
            client.get('/api/content/page/missing', headers={'X-Tenant-Id': 'site-a'}).status_code
            == 404
        )
        assert (
            client.get('/api/search?q=notes', headers={'X-Tenant-Id': 'site-a'}).status_code == 200
        )
    finally:
        app.dependency_overrides.clear()


def test_form_submission_is_queued_and_idempotently_replayed(monkeypatch):
    monkeypatch.setattr(
        'api.routes.site_content.rate_limit.incr_and_check_tenant_detailed',
        lambda *_args: (1, False, 0),
    )
    fake = FakeSiteContentService()
    app.dependency_overrides[get_site_content_service] = lambda: fake
    try:
        client = TestClient(app)
        headers = {'X-Tenant-Id': 'site-a', 'Idempotency-Key': 'request-1', 'X-Request-Id': 'req-1'}
        first = client.post(
            '/api/forms/contact',
            headers=headers,
            json={'payload': {'message': 'hello'}, 'consent': {'essential': True}},
        )
        second = client.post(
            '/api/forms/contact',
            headers=headers,
            json={'payload': {'message': 'hello'}, 'consent': {'essential': True}},
        )
        assert first.status_code == second.status_code == 202
        assert first.json()['replayed'] is False
        assert second.json()['replayed'] is True
    finally:
        app.dependency_overrides.clear()


def test_invalid_tenant_and_typed_service_failure_do_not_leak_details():
    class BrokenService(FakeSiteContentService):
        def list_content(self, **_kwargs):
            raise RuntimeError('database-password-must-not-leak')

    app.dependency_overrides[get_site_content_service] = BrokenService
    try:
        client = TestClient(app)
        invalid = client.get('/api/content', headers={'X-Tenant-Id': '../site'})
        assert invalid.status_code == 400
        failed = client.get('/api/content', headers={'X-Tenant-Id': 'site-a'})
        assert failed.status_code == 503
        assert failed.json() == {'detail': 'site_content_temporarily_unavailable'}
        assert 'password' not in failed.text
    finally:
        app.dependency_overrides.clear()
