from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from api.main import app


USER_ID = UUID('00000000-0000-0000-0000-000000000901')


def _permit(monkeypatch, *, age_seconds=0, recently_authenticated=True):
    principal = SimpleNamespace(
        user_id=USER_ID,
        authenticated_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
        recently_authenticated=recently_authenticated,
    )
    monkeypatch.setattr(
        'api.routes.tenant.require_authenticated_principal', lambda request: principal
    )
    monkeypatch.setattr('api.routes.tenant.require_permission', lambda **kwargs: {'role': 'owner'})


def test_quota_list_is_tenant_scoped(monkeypatch):
    _permit(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        'api.routes.tenant.tenant_quota.list_quotas',
        lambda **kwargs: captured.update(kwargs) or [{'quotaKey': 'jobs', 'available': 4}],
    )
    response = TestClient(app).get(
        '/api/tenants/tenant-one/quotas', headers={'X-Tenant-Id': 'tenant-one'}
    )
    assert response.status_code == 200
    assert response.json()['quotas'][0]['available'] == 4
    assert captured == {'tenant_id': 'tenant-one'}


def test_quota_path_header_mismatch_fails_closed(monkeypatch):
    _permit(monkeypatch)
    response = TestClient(app).get(
        '/api/tenants/tenant-one/quotas', headers={'X-Tenant-Id': 'tenant-two'}
    )
    assert response.status_code in {400, 403, 404}


def test_reservation_requires_explicit_recent_reauthentication(monkeypatch):
    _permit(monkeypatch, recently_authenticated=False)
    response = TestClient(app).post(
        '/api/tenants/tenant-one/quotas/jobs/reservations',
        headers={'X-Tenant-Id': 'tenant-one'},
        json={'amount': 1, 'reservationId': 'job.reserve-001'},
    )
    assert response.status_code == 403
    assert response.json() == {'detail': 'recent_reauthentication_required'}

    _permit(monkeypatch, age_seconds=301)
    response = TestClient(app).post(
        '/api/tenants/tenant-one/quotas/jobs/reservations',
        headers={'X-Tenant-Id': 'tenant-one'},
        json={'amount': 1, 'reservationId': 'job.reserve-001'},
    )
    assert response.status_code == 403
    assert response.json() == {'detail': 'recent_reauthentication_required'}


def test_reservation_and_settlement_are_tenant_bound(monkeypatch):
    _permit(monkeypatch)
    calls = []
    monkeypatch.setattr(
        'api.routes.tenant.tenant_quota.reserve',
        lambda **kwargs: calls.append(('reserve', kwargs))
        or {'status': 'reserved', 'reservationId': kwargs['reservation_id']},
    )
    monkeypatch.setattr(
        'api.routes.tenant.tenant_quota.settle',
        lambda **kwargs: calls.append(('settle', kwargs))
        or {'status': 'committed', 'reservationId': kwargs['reservation_id']},
    )
    client = TestClient(app)
    reserved = client.post(
        '/api/tenants/tenant-one/quotas/jobs/reservations',
        headers={'X-Tenant-Id': 'tenant-one'},
        json={'amount': 2, 'reservationId': 'job.reserve-002'},
    )
    settled = client.post(
        '/api/tenants/tenant-one/quotas/reservations/job.reserve-002/settle',
        headers={'X-Tenant-Id': 'tenant-one'},
        json={'commit': True},
    )
    assert reserved.status_code == settled.status_code == 200
    assert calls == [
        (
            'reserve',
            {
                'tenant_id': 'tenant-one',
                'quota_key': 'jobs',
                'amount': 2,
                'reservation_id': 'job.reserve-002',
            },
        ),
        (
            'settle',
            {'tenant_id': 'tenant-one', 'reservation_id': 'job.reserve-002', 'commit': True},
        ),
    ]


def test_repository_conflicts_are_stable_public_errors(monkeypatch):
    _permit(monkeypatch)

    def exhausted(**kwargs):
        raise __import__('api.repositories.tenant_quota', fromlist=['QuotaRepositoryError']).QuotaRepositoryError(
            'quota:exhausted'
        )

    monkeypatch.setattr('api.routes.tenant.tenant_quota.reserve', exhausted)
    response = TestClient(app).post(
        '/api/tenants/tenant-one/quotas/jobs/reservations',
        headers={'X-Tenant-Id': 'tenant-one'},
        json={'amount': 2, 'reservationId': 'job.reserve-003'},
    )
    assert response.status_code == 409
    assert response.json() == {'detail': 'quota:exhausted'}
