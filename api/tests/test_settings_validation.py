import importlib
import base64
import pytest


def test_missing_required_env_raises(monkeypatch):
    # Simulate staging environment with missing required vars
    monkeypatch.setenv('ENV', 'staging')
    for var in [
        'JWT_SECRET',
        'TOKEN_PEPPER',
        'IDENTITY_ENCRYPTION_KEY',
        'FRONTEND_URL',
        'OAUTH_STATE_SECRET',
    ]:
        monkeypatch.delenv(var, raising=False)

    # Reload settings to apply env changes
    with pytest.raises(RuntimeError) as excinfo:
        import api.settings as s

        importlib.reload(s)

    assert 'Missing required env var(s):' in str(excinfo.value)


def test_staging_requires_valid_private_workspace_storage_configuration(monkeypatch):
    from api.settings import Settings

    required = {
        'ENV': 'staging',
        'JWT_SECRET': 'fixture-jwt',
        'TOKEN_PEPPER': 'fixture-pepper-long-enough',
        'IDENTITY_ENCRYPTION_KEY': 'fixture-identity',
        'FRONTEND_URL': 'https://example.test',
        'OAUTH_STATE_SECRET': 'fixture-state',
        'CONTENT_WORKSPACE_STORAGE_ROOT': '/var/lib/base2/content-workspace',
        'CONTENT_WORKSPACE_STORAGE_KEY': base64.urlsafe_b64encode(b'k' * 32).decode(),
    }
    for key, value in required.items():
        monkeypatch.setenv(key, value)
    assert Settings().CONTENT_WORKSPACE_STORAGE_ROOT.startswith('/')

    monkeypatch.setenv('CONTENT_WORKSPACE_STORAGE_KEY', 'too-short')
    with pytest.raises(RuntimeError, match='CONTENT_WORKSPACE_STORAGE_KEY'):
        Settings()
    monkeypatch.setenv(
        'CONTENT_WORKSPACE_STORAGE_KEY', base64.urlsafe_b64encode(b'k' * 32).decode()
    )
    monkeypatch.setenv('CONTENT_WORKSPACE_STORAGE_ROOT', 'relative')
    with pytest.raises(RuntimeError, match='storage configuration'):
        Settings()
