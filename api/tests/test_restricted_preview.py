import asyncio
from unittest.mock import AsyncMock

import pytest

from api.security.restricted_preview import (
    RestrictedPreviewMiddleware, require_media_enabled, restricted_preview,
)


@pytest.mark.parametrize('path', ['/api/media/v1/uploads', '/api/content/v1/assets/uploads',
                                  '/api/content/v1/import', '/media/v1', '/content', '/api/media/'])
def test_restricted_blocks_before_body_read(monkeypatch, path):
    monkeypatch.setenv('BASE2_PREVIEW_MODE', 'restricted')
    app, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
    asyncio.run(RestrictedPreviewMiddleware(app)({'type': 'http', 'path': path}, receive, send))
    app.assert_not_called()
    receive.assert_not_called()
    assert send.call_args_list[0].args[0]['status'] == 503


@pytest.mark.parametrize('mode,path', [('full', '/api/media/v1/uploads'),
                                      ('restricted', '/api/auth/login'),
                                      ('restricted', '/api/settings/profile'),
                                      ('restricted', '/api/media-other')])
def test_unaffected_routes(monkeypatch, mode, path):
    monkeypatch.setenv('BASE2_PREVIEW_MODE', mode)
    app, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
    asyncio.run(RestrictedPreviewMiddleware(app)({'type': 'http', 'path': path}, receive, send))
    app.assert_awaited_once()


def test_default_and_invalid_mode(monkeypatch):
    monkeypatch.delenv('BASE2_PREVIEW_MODE', raising=False)
    assert restricted_preview() is False
    require_media_enabled()
    monkeypatch.setenv('BASE2_PREVIEW_MODE', 'typo')
    with pytest.raises(ValueError, match='invalid_preview_mode'):
        restricted_preview()
    monkeypatch.setenv('BASE2_PREVIEW_MODE', 'restricted')
    with pytest.raises(ValueError, match='media_disabled'):
        require_media_enabled()


def test_media_jobs_stop_before_repository_access(monkeypatch):
    from api import tasks
    monkeypatch.setenv('BASE2_PREVIEW_MODE', 'restricted')
    def forbidden(*args, **kwargs):
        raise AssertionError('repository must not be reached')
    for name in ('due_media_scans', 'due_media_exports', 'apply_due_media_governance', '_require_tenant_serving'):
        monkeypatch.setattr(tasks, name, forbidden)
    assert tasks.replay_workspace_media_scans() == 0
    assert tasks.replay_media_exports() == 0
    with pytest.raises(ValueError, match='media_disabled'):
        tasks.scan_workspace_asset_task('site', 'asset', 'job', 1, 'lease')
    with pytest.raises(ValueError, match='media_disabled'):
        tasks.process_media_export_task('site', 'export')
    with pytest.raises(ValueError, match='media_disabled'):
        tasks.apply_media_governance()


def test_application_wires_media_guard(monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import app
    monkeypatch.setenv('BASE2_PREVIEW_MODE', 'restricted')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/media/v1/uploads', content=b'not a valid upload')
    assert response.status_code == 503
    assert response.json()['detail'] == 'media_disabled_in_restricted_preview'
