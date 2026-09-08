from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from api.main import app

USER_ID = UUID('00000000-0000-0000-0000-000000000801')
INCIDENT_ID = UUID('00000000-0000-0000-0000-000000000802')


def principal(*, age_seconds=0, recently_authenticated=True):
    return SimpleNamespace(
        user_id=USER_ID,
        authenticated_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
        recently_authenticated=recently_authenticated,
    )


def permit(monkeypatch, *, age_seconds=0, role='owner', recently_authenticated=True):
    monkeypatch.setattr(
        'api.routes.operations.require_authenticated_principal',
        lambda request: principal(
            age_seconds=age_seconds, recently_authenticated=recently_authenticated
        ),
    )
    monkeypatch.setattr(
        'api.routes.operations.require_permission',
        lambda **kwargs: {'role': role},
    )


def test_summary_and_incidents_are_tenant_bound(monkeypatch):
    permit(monkeypatch)
    captured = []
    monkeypatch.setattr(
        'api.routes.operations.repository.summary',
        lambda **kwargs: captured.append(kwargs)
        or {
            'services': {'enabled': 2, 'total': 2},
            'incidents': {},
            'synthetics24h': {'passed': 1},
        },
    )
    monkeypatch.setattr(
        'api.routes.operations.repository.list_incidents',
        lambda **kwargs: captured.append(kwargs) or [],
    )
    client = TestClient(app)
    summary = client.get('/api/operations/v1/summary', headers={'X-Tenant-Id': 'tenant-one'})
    incidents = client.get(
        '/api/operations/v1/incidents?limit=20', headers={'X-Tenant-Id': 'tenant-one'}
    )
    assert summary.status_code == incidents.status_code == 200
    assert summary.json()['schemaVersion'] == 1
    assert incidents.json() == {'schemaVersion': 1, 'incidents': []}
    assert captured == [{'tenant_id': 'tenant-one'}, {'tenant_id': 'tenant-one', 'limit': 20}]


def test_permission_denial_is_generic(monkeypatch):
    monkeypatch.setattr(
        'api.routes.operations.require_authenticated_principal', lambda request: principal()
    )
    monkeypatch.setattr(
        'api.routes.operations.require_permission',
        lambda **kwargs: (_ for _ in ()).throw(PermissionError('denied')),
    )
    response = TestClient(app).get(
        '/api/operations/v1/summary', headers={'X-Tenant-Id': 'tenant-one'}
    )
    assert response.status_code == 404
    assert response.json() == {'detail': 'operations_not_found'}


def test_acknowledgement_requires_recent_auth_and_exact_state(monkeypatch):
    permit(monkeypatch, age_seconds=301)
    client = TestClient(app)
    stale = client.post(
        f'/api/operations/v1/incidents/{INCIDENT_ID}/acknowledge',
        headers={'X-Tenant-Id': 'tenant-one'},
    )
    assert stale.status_code == 403
    assert stale.json() == {'detail': 'recent_reauthentication_required'}
    permit(monkeypatch, recently_authenticated=False)
    refreshed = client.post(
        f'/api/operations/v1/incidents/{INCIDENT_ID}/acknowledge',
        headers={'X-Tenant-Id': 'tenant-one'},
    )
    assert refreshed.status_code == 403
    assert refreshed.json() == {'detail': 'recent_reauthentication_required'}
    permit(monkeypatch)
    monkeypatch.setattr('api.routes.operations.repository.acknowledge', lambda **kwargs: False)
    conflict = client.post(
        f'/api/operations/v1/incidents/{INCIDENT_ID}/acknowledge',
        headers={'X-Tenant-Id': 'tenant-one'},
    )
    assert conflict.status_code == 409
    assert conflict.json() == {'detail': 'incident_state_conflict'}


def test_acknowledgement_uses_tenant_owner_and_uuid(monkeypatch):
    permit(monkeypatch, role='admin')
    captured = {}
    monkeypatch.setattr(
        'api.routes.operations.repository.acknowledge',
        lambda **kwargs: captured.update(kwargs) or True,
    )
    response = TestClient(app).post(
        f'/api/operations/v1/incidents/{INCIDENT_ID}/acknowledge',
        headers={'X-Tenant-Id': 'tenant-two'},
    )
    assert response.status_code == 200
    assert response.json() == {'status': 'acknowledged', 'incidentId': str(INCIDENT_ID)}
    assert captured == {
        'tenant_id': 'tenant-two',
        'incident_id': INCIDENT_ID,
        'owner_ref': f'admin:{USER_ID}',
    }
