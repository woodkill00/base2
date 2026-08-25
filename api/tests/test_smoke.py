from fastapi.testclient import TestClient

# Pytest (notably newer versions) may not automatically prepend the project root
# to sys.path when importing test modules. Ensure the API app module is importable
# both when running from repo root and when code is copied into a container at /app.

import api.main as main


def test_health_exists(monkeypatch):
    monkeypatch.setattr(
        main,
        'READINESS_PROBES',
        {name: (lambda: True) for name in ('database', 'schema', 'redis', 'celery')},
    )
    client = TestClient(main.app)
    r = client.get('/api/health')
    assert r.status_code == 200
    j = r.json()
    assert 'ok' in j and j['ok'] is True
