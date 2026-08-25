import importlib
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
