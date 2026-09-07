from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import media_library
from api.security.request_auth import PublicPrincipal
from api.security.upload_capacity import UploadCapacityError


ASSET_ID = '00000000-0000-0000-0000-000000000110'
app = FastAPI()
app.include_router(media_library.router, prefix='/api')


class Repository:
    def list_assets(self, **kwargs):
        assert kwargs['site_id'] == 'base2-obsidian'
        return {'items': [], 'nextOffset': None, 'indexStatus': 'current'}

    def get_asset(self, **kwargs):
        assert kwargs['site_id'] == 'base2-obsidian'
        return {'id': str(kwargs['asset_id']), 'status': 'ready'}

    def update_metadata(self, **kwargs):
        assert kwargs['expected_version'] == 2
        return {'id': str(kwargs['asset_id']), 'revision': 1, 'version': 3}

    def list_references(self, **kwargs):
        assert kwargs['site_id'] == 'base2-obsidian'
        return {'items': []}

    def destructive_preview(self, **kwargs):
        return {'assetId': str(kwargs['asset_id']), 'allowed': True}

    def transition_asset(self, **kwargs):
        assert kwargs['expected_version'] == 2
        assert kwargs['idempotency_key'] == 'request-123'
        return {'id': str(kwargs['asset_id']), 'status': kwargs['target'], 'version': 3}

    def create_export(self, **kwargs):
        assert len(kwargs['request_digest']) == 64
        assert kwargs['projection'] == {
            'fields': ['id', 'filename'],
            'assetIds': [ASSET_ID],
            'filters': {},
        }
        return {'id': ASSET_ID, 'status': 'queued', 'replayed': False}

    def list_collections(self, **kwargs):
        assert kwargs['site_id'] == 'base2-obsidian'
        return {'items': []}

    def create_collection(self, **kwargs):
        assert kwargs['title'] == 'Launch assets'
        return {'id': ASSET_ID, 'title': kwargs['title'], 'version': 1}

    def add_collection_assets(self, **kwargs):
        assert kwargs['asset_ids'] == [UUID(ASSET_ID)]
        return {'collectionId': str(kwargs['collection_id']), 'added': 1, 'requested': 1}

    def list_jobs(self, **kwargs):
        return {'items': []}

    def retry_job(self, **kwargs):
        return {'id': str(kwargs['job_id']), 'status': 'queued', 'attempt': 1}

    def get_export(self, **kwargs):
        return {'id': str(kwargs['export_id']), 'status': 'ready', 'sha256': 'a' * 64}


@pytest.fixture(autouse=True)
def scoped(monkeypatch):
    principal = PublicPrincipal(UUID(int=110), datetime.now(UTC), True)
    monkeypatch.setattr(
        media_library, 'require_authenticated_principal', lambda _request: principal
    )
    monkeypatch.setattr(media_library, 'require_tenant', lambda _request: 'base2-obsidian')
    monkeypatch.setattr(media_library, 'authorize', lambda **_kwargs: {})
    monkeypatch.setattr(media_library, 'get_repository', Repository)
    monkeypatch.setattr(
        media_library, 'incr_and_check_tenant_detailed', lambda *_args: (1, False, 0)
    )


def test_capabilities_are_closed_and_do_not_expose_storage_details():
    response = TestClient(app).get('/api/media/v1/capabilities')
    assert response.status_code == 200
    body = response.json()
    assert body['schemaVersion'] == 1
    assert all(set(item) == {'mediaType', 'extensions', 'delivery'} for item in body['formats'])
    assert 'storage' not in str(body).lower()


def test_list_and_detail_are_scoped():
    client = TestClient(app)
    assert client.get('/api/media/v1/assets?state=ready&limit=25').status_code == 200
    assert client.get(f'/api/media/v1/assets/{ASSET_ID}').status_code == 200
    assert client.get('/api/media/v1/assets?state=unknown').status_code == 422
    assert client.get('/api/media/v1/assets?media_type=text/html').status_code == 422


def test_asset_cursor_is_opaque_signed_and_offset_exclusive(monkeypatch):
    class CursorRepository(Repository):
        def list_assets(self, **kwargs):
            if kwargs['cursor_after']:
                assert kwargs['cursor_after'][1] == UUID(ASSET_ID)
                return {
                    'items': [],
                    'nextAnchor': None,
                    'nextOffset': None,
                    'indexStatus': 'current',
                }
            return {
                'items': [],
                'nextOffset': 25,
                'indexStatus': 'current',
                'nextAnchor': {'id': ASSET_ID, 'updatedAt': '2026-09-06T12:00:00+00:00'},
            }

    monkeypatch.setattr(media_library.settings, 'JWT_SECRET', 'c' * 64)
    monkeypatch.setattr(media_library, 'get_repository', CursorRepository)
    client = TestClient(app)
    first = client.get('/api/media/v1/assets').json()
    assert first['nextCursor'] and ASSET_ID not in first['nextCursor']
    assert client.get(f'/api/media/v1/assets?cursor={first["nextCursor"]}').status_code == 200
    assert client.get(f'/api/media/v1/assets?cursor={first["nextCursor"]}x').status_code == 422
    assert (
        client.get(f'/api/media/v1/assets?cursor={first["nextCursor"]}&offset=1').status_code == 422
    )
    assert (
        client.get(f'/api/media/v1/assets?cursor={first["nextCursor"]}&state=ready').status_code
        == 422
    )


def test_metadata_contract_rejects_unknown_fields_and_requires_version():
    client = TestClient(app)
    good = {
        'locale': 'en',
        'altText': 'A useful description',
        'decorative': False,
        'caption': '',
        'credit': '',
        'licenseCode': '',
        'visibility': 'private',
    }
    assert client.put(f'/api/media/v1/assets/{ASSET_ID}/metadata', json=good).status_code == 422
    response = client.put(
        f'/api/media/v1/assets/{ASSET_ID}/metadata',
        json={**good, 'unknown': True},
        headers={'If-Match': '"2"'},
    )
    assert response.status_code == 422
    response = client.put(
        f'/api/media/v1/assets/{ASSET_ID}/metadata',
        json=good,
        headers={'If-Match': '"2"'},
    )
    assert response.status_code == 200 and response.json()['version'] == 3


def test_content_transfer_uses_header_grants_and_safe_delivery_headers(monkeypatch):
    monkeypatch.setattr(media_library, 'get_artifact_store', lambda: object())
    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        'validate_asset_upload_grant',
        lambda _self, **_kwargs: {'expectedBytes': 8},
    )
    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        'complete_asset_upload',
        lambda _self, **kwargs: {
            'id': str(kwargs['asset_id']),
            'status': 'quarantined',
            'sha256': 'a' * 64,
        },
    )
    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        'read_asset_content',
        lambda _self, **_kwargs: {
            'content': b'safe-png',
            'media_type': 'image/png',
            'sha256': 'a' * 64,
        },
    )
    client = TestClient(app)
    response = client.put(
        f'/api/media/v1/assets/{ASSET_ID}/content',
        content=b'safe-png',
        headers={'Upload-Grant': 'g' * 64, 'Content-Type': 'image/png'},
    )
    assert response.status_code == 200 and response.json()['status'] == 'quarantined'
    response = client.get(
        f'/api/media/v1/assets/{ASSET_ID}/content',
        headers={'Download-Grant': 'g' * 64},
    )
    assert response.status_code == 200 and response.content == b'safe-png'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['content-security-policy'] == "default-src 'none'; sandbox"
    assert response.headers['referrer-policy'] == 'no-referrer'


def test_content_transfer_rejects_exhausted_upload_capacity(monkeypatch):
    class Exhausted:
        async def __aenter__(self):
            raise UploadCapacityError('upload_capacity_exhausted')

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(media_library, 'upload_completion_slot', lambda: Exhausted())
    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        'validate_asset_upload_grant',
        lambda _self, **_kwargs: {'expectedBytes': 8},
    )
    response = TestClient(app).put(
        f'/api/media/v1/assets/{ASSET_ID}/content',
        content=b'safe-png',
        headers={'Upload-Grant': 'g' * 64, 'Content-Type': 'image/png'},
    )
    assert response.status_code == 429
    assert response.json()['detail'] == 'media_upload_capacity_exhausted'
    assert response.headers['retry-after'] == '2'


def test_content_transfer_rejects_invalid_grant_before_capacity(monkeypatch):
    entered = False

    class ForbiddenSlot:
        async def __aenter__(self):
            nonlocal entered
            entered = True
            raise AssertionError('capacity must not be acquired')

        async def __aexit__(self, *_args):
            return False

    def reject(_self, **_kwargs):
        raise ValueError('content_upload_grant_invalid')

    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        'validate_asset_upload_grant',
        reject,
    )
    monkeypatch.setattr(media_library, 'upload_completion_slot', lambda: ForbiddenSlot())
    response = TestClient(app).put(
        f'/api/media/v1/assets/{ASSET_ID}/content',
        content=b'slow-body-never-admitted',
        headers={'Upload-Grant': 'invalid-grant-that-is-long-enough'},
    )
    assert response.status_code == 422
    assert response.json()['detail'] == 'media_upload_grant_invalid'
    assert entered is False


@pytest.mark.parametrize(
    'payload',
    [
        {
            'filename': '../../escape.png',
            'mediaType': 'image/png',
            'byteSize': 1,
            'sha256': 'a' * 64,
        },
        {'filename': 'active.svg', 'mediaType': 'image/png', 'byteSize': 1, 'sha256': 'a' * 64},
        {'filename': 'page.html', 'mediaType': 'text/html', 'byteSize': 1, 'sha256': 'a' * 64},
    ],
)
def test_upload_contract_rejects_hostile_metadata_before_repository(monkeypatch, payload):
    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository,
        'create_asset_upload',
        lambda *_args, **_kwargs: pytest.fail('repository must not be called'),
    )
    response = TestClient(app).post('/api/media/v1/uploads', json=payload)
    assert response.status_code == 422


def test_upload_admission_is_idempotent_bounded_and_rate_limited(monkeypatch):
    observed = {}

    def create(_self, **kwargs):
        observed.update(kwargs)
        return {'id': ASSET_ID, 'status': 'pending', 'uploadGrant': 'g' * 64}

    monkeypatch.setattr(
        media_library.PostgresContentWorkspaceRepository, 'create_asset_upload', create
    )
    client = TestClient(app)
    payload = {
        'filename': 'safe.png',
        'mediaType': 'image/png',
        'byteSize': 8,
        'sha256': 'a' * 64,
    }
    assert client.post('/api/media/v1/uploads', json=payload).status_code == 422
    response = client.post(
        '/api/media/v1/uploads', json=payload, headers={'Idempotency-Key': 'upload-110'}
    )
    assert response.status_code == 201
    assert observed['idempotency_key'] == 'upload-110'
    assert observed['maximum_active_uploads'] == 100
    assert observed['maximum_pending_processing'] == 200
    monkeypatch.setattr(
        media_library, 'incr_and_check_tenant_detailed', lambda *_args: (31, True, 17)
    )
    response = client.post(
        '/api/media/v1/uploads', json=payload, headers={'Idempotency-Key': 'upload-111'}
    )
    assert response.status_code == 429 and response.headers['retry-after'] == '17'


def test_reference_preview_lifecycle_and_export_contracts_are_bounded():
    client = TestClient(app)
    assert client.get(f'/api/media/v1/assets/{ASSET_ID}/references').status_code == 200
    assert client.get(f'/api/media/v1/assets/{ASSET_ID}/destructive-preview').status_code == 200
    response = client.post(
        f'/api/media/v1/assets/{ASSET_ID}/lifecycle',
        json={'target': 'archived'},
        headers={'If-Match': '"2"', 'Idempotency-Key': 'request-123'},
    )
    assert response.status_code == 200 and response.json()['status'] == 'archived'
    response = client.post(
        '/api/media/v1/exports',
        json={'outputFormat': 'csv', 'assetIds': [ASSET_ID], 'projection': ['id', 'filename']},
        headers={'Idempotency-Key': 'request-123'},
    )
    assert response.status_code == 202 and response.json()['status'] == 'queued'
    assert (
        client.post(
            '/api/media/v1/exports',
            json={'outputFormat': 'csv', 'projection': ['id'], 'assetIds': []},
            headers={'Idempotency-Key': 'request-123'},
        ).status_code
        == 422
    )
    assert (
        client.post(
            '/api/media/v1/exports',
            json={'outputFormat': 'csv', 'projection': ['id'], 'assetIds': [ASSET_ID, ASSET_ID]},
            headers={'Idempotency-Key': 'request-123'},
        ).status_code
        == 422
    )
    assert (
        client.post(
            '/api/media/v1/exports',
            json={'outputFormat': 'csv', 'assetIds': [ASSET_ID], 'projection': ['id', 'id']},
            headers={'Idempotency-Key': 'request-123'},
        ).status_code
        == 422
    )


def test_lifecycle_route_returns_first_and_exact_replay_receipts(monkeypatch):
    class ReplayRepository(Repository):
        calls = 0

        def transition_asset(self, **kwargs):
            self.calls += 1
            return {
                'id': str(kwargs['asset_id']),
                'status': kwargs['target'],
                'version': 3,
                'replayed': self.calls > 1,
            }

    repository = ReplayRepository()
    monkeypatch.setattr(media_library, 'get_repository', lambda: repository)
    request = {
        'json': {'target': 'archived'},
        'headers': {'If-Match': '2', 'Idempotency-Key': 'request-123'},
    }
    client = TestClient(app)
    first = client.post(f'/api/media/v1/assets/{ASSET_ID}/lifecycle', **request)
    replay = client.post(f'/api/media/v1/assets/{ASSET_ID}/lifecycle', **request)
    assert first.status_code == replay.status_code == 200
    assert first.json()['replayed'] is False
    assert replay.json() == {**first.json(), 'replayed': True}


def test_sensitive_media_action_requires_recent_auth_and_cookie_csrf(monkeypatch):
    stale = PublicPrincipal(UUID(int=110), datetime.now(UTC), False)
    monkeypatch.setattr(media_library, 'require_authenticated_principal', lambda _request: stale)
    response = TestClient(app).get(f'/api/media/v1/assets/{ASSET_ID}/destructive-preview')
    assert response.status_code == 401

    stale_claim = PublicPrincipal(UUID(int=110), datetime.now(UTC) - timedelta(minutes=6), True)
    monkeypatch.setattr(
        media_library, 'require_authenticated_principal', lambda _request: stale_claim
    )
    response = TestClient(app).get(f'/api/media/v1/assets/{ASSET_ID}/destructive-preview')
    assert response.status_code == 401

    fresh = PublicPrincipal(UUID(int=110), datetime.now(UTC), True)
    monkeypatch.setattr(media_library, 'require_authenticated_principal', lambda _request: fresh)
    monkeypatch.setattr(media_library.settings, 'SESSION_COOKIE_NAME', 'session')
    monkeypatch.setattr(media_library.settings, 'CSRF_COOKIE_NAME', 'csrf')
    client = TestClient(app)
    client.cookies.set('session', 'present')
    client.cookies.set('csrf', 'expected')
    assert client.get(f'/api/media/v1/assets/{ASSET_ID}/destructive-preview').status_code == 403
    assert (
        client.get(
            f'/api/media/v1/assets/{ASSET_ID}/destructive-preview',
            headers={'X-CSRF-Token': 'expected'},
        ).status_code
        == 200
    )


def test_collection_job_and_export_routes_are_closed_and_scoped():
    client = TestClient(app)
    assert client.get('/api/media/v1/collections').status_code == 200
    response = client.post(
        '/api/media/v1/collections',
        json={'title': 'Launch assets', 'visibility': 'private', 'sharedRoles': []},
    )
    assert response.status_code == 201
    assert (
        client.post(
            '/api/media/v1/collections',
            json={'title': 'Bad', 'visibility': 'private', 'sharedRoles': ['viewer']},
        ).status_code
        == 422
    )
    response = client.post(
        f'/api/media/v1/collections/{ASSET_ID}/assets',
        json={'assetIds': [ASSET_ID]},
    )
    assert response.status_code == 200 and response.json()['added'] == 1
    assert client.get('/api/media/v1/jobs?limit=25').status_code == 200
    response = client.post(f'/api/media/v1/jobs/{ASSET_ID}/retry')
    assert response.status_code == 200 and response.json()['status'] == 'queued'
    response = client.get(f'/api/media/v1/exports/{ASSET_ID}')
    assert response.status_code == 200 and response.json()['status'] == 'ready'


def test_collection_unknown_fields_duplicates_and_bounds_fail_before_repository():
    client = TestClient(app)
    assert (
        client.post(
            '/api/media/v1/collections',
            json={'title': 'Bad', 'visibility': 'private', 'sharedRoles': [], 'extra': True},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f'/api/media/v1/collections/{ASSET_ID}/assets',
            json={'assetIds': [ASSET_ID, ASSET_ID]},
        ).status_code
        == 422
    )
    assert client.get('/api/media/v1/jobs?limit=101').status_code == 422


class FailureRepository:
    def __init__(self, code='dependency'):
        self.code = code

    def __getattr__(self, _name):
        def fail(**_kwargs):
            if self.code == 'dependency':
                raise RuntimeError('private dependency detail')
            raise ValueError(self.code)

        return fail


@pytest.mark.parametrize(
    ('method', 'path', 'kwargs'),
    [
        ('get', '/api/media/v1/assets', {}),
        ('get', f'/api/media/v1/assets/{ASSET_ID}', {}),
        ('get', f'/api/media/v1/assets/{ASSET_ID}/references', {}),
        ('get', f'/api/media/v1/assets/{ASSET_ID}/destructive-preview', {}),
        (
            'post',
            f'/api/media/v1/assets/{ASSET_ID}/lifecycle',
            {
                'json': {'target': 'archived'},
                'headers': {'If-Match': '2', 'Idempotency-Key': 'request-123'},
            },
        ),
        (
            'post',
            '/api/media/v1/exports',
            {
                'json': {'outputFormat': 'csv', 'assetIds': [ASSET_ID], 'projection': ['id']},
                'headers': {'Idempotency-Key': 'request-123'},
            },
        ),
        ('get', '/api/media/v1/collections', {}),
        (
            'post',
            '/api/media/v1/collections',
            {
                'json': {'title': 'Safe', 'visibility': 'private', 'sharedRoles': []},
            },
        ),
        (
            'post',
            f'/api/media/v1/collections/{ASSET_ID}/assets',
            {
                'json': {'assetIds': [ASSET_ID]},
            },
        ),
        ('get', '/api/media/v1/jobs', {}),
        ('post', f'/api/media/v1/jobs/{ASSET_ID}/retry', {}),
        ('get', f'/api/media/v1/exports/{ASSET_ID}', {}),
    ],
)
def test_dependency_failures_are_redacted_and_typed(monkeypatch, method, path, kwargs):
    monkeypatch.setattr(media_library, 'get_repository', lambda: FailureRepository())
    response = getattr(TestClient(app), method)(path, **kwargs)
    assert response.status_code == 503
    assert response.json() == {'detail': 'media_dependency_unavailable'}
    assert 'private' not in response.text


@pytest.mark.parametrize(
    ('code', 'method', 'path', 'kwargs', 'status'),
    [
        ('media_not_found', 'get', f'/api/media/v1/assets/{ASSET_ID}/references', {}, 404),
        (
            'media_transition_blocked',
            'get',
            f'/api/media/v1/assets/{ASSET_ID}/destructive-preview',
            {},
            423,
        ),
        (
            'media_version_conflict',
            'post',
            f'/api/media/v1/assets/{ASSET_ID}/lifecycle',
            {
                'json': {'target': 'archived'},
                'headers': {'If-Match': '2', 'Idempotency-Key': 'request-123'},
            },
            409,
        ),
        (
            'media_idempotency_conflict',
            'post',
            f'/api/media/v1/assets/{ASSET_ID}/lifecycle',
            {
                'json': {'target': 'archived'},
                'headers': {'If-Match': '2', 'Idempotency-Key': 'request-123'},
            },
            409,
        ),
        (
            'media_not_found',
            'post',
            f'/api/media/v1/collections/{ASSET_ID}/assets',
            {
                'json': {'assetIds': [ASSET_ID]},
            },
            404,
        ),
        ('media_job_retry_blocked', 'post', f'/api/media/v1/jobs/{ASSET_ID}/retry', {}, 409),
        ('media_not_found', 'get', f'/api/media/v1/exports/{ASSET_ID}', {}, 404),
    ],
)
def test_domain_failures_use_bounded_status_codes(monkeypatch, code, method, path, kwargs, status):
    monkeypatch.setattr(media_library, 'get_repository', lambda: FailureRepository(code))
    response = getattr(TestClient(app), method)(path, **kwargs)
    assert response.status_code == status and response.json() == {'detail': code}
