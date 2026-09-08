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
        'DB_SSLMODE': 'verify-full',
        'DB_SSLROOTCERT': '/run/secrets/database-ca.pem',
        'OPERATIONS_ALERT_INTEGRITY_KEY_FILE': '/run/secrets/operations-alert-integrity',
        'OPERATIONS_ALERT_RECEIPT_KEY_FILE': '/run/secrets/operations-alert-receipt',
        'OPERATIONS_ALERT_WEBHOOK_URL_FILE': '/run/secrets/operations-alert-webhook',
        'OPERATIONS_RECEIPT_INTEGRITY_KEY_FILE': '/run/secrets/operations-receipt-integrity',
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


def test_staging_requires_verified_database_tls(monkeypatch):
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
        'DB_SSLROOTCERT': '/run/secrets/database-ca.pem',
        'OPERATIONS_ALERT_INTEGRITY_KEY_FILE': '/run/secrets/operations-alert-integrity',
        'OPERATIONS_ALERT_RECEIPT_KEY_FILE': '/run/secrets/operations-alert-receipt',
        'OPERATIONS_ALERT_WEBHOOK_URL_FILE': '/run/secrets/operations-alert-webhook',
        'OPERATIONS_RECEIPT_INTEGRITY_KEY_FILE': '/run/secrets/operations-receipt-integrity',
    }
    for key, value in required.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('DB_SSLMODE', 'require')
    with pytest.raises(RuntimeError, match='TLS verify-full'):
        Settings()
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    assert Settings().DB_SSLMODE == 'verify-full'


def test_operations_alert_activation_requires_distinct_absolute_secret_files(monkeypatch):
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
        'DB_SSLMODE': 'verify-full',
        'DB_SSLROOTCERT': '/run/secrets/database-ca.pem',
        'OPERATIONS_ALERTS_ENABLED': 'true',
    }
    for key, value in required.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match='OPERATIONS_ALERT_INTEGRITY_KEY_FILE'):
        Settings()
    for name in (
        'OPERATIONS_ALERT_INTEGRITY_KEY_FILE',
        'OPERATIONS_ALERT_RECEIPT_KEY_FILE',
        'OPERATIONS_ALERT_WEBHOOK_URL_FILE',
    ):
        monkeypatch.setenv(name, f'/run/secrets/{name.lower()}')
    assert Settings().OPERATIONS_ALERTS_ENABLED is True
    monkeypatch.setenv('OPERATIONS_ALERT_WEBHOOK_URL_FILE', '/run/secrets/operations_alert_receipt_key_file')
    with pytest.raises(RuntimeError, match='independently scoped'):
        Settings()
