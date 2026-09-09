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


@pytest.mark.parametrize(
    ('name', 'value', 'message'),
    [
        ('DB_SSLMODE', 'disable', 'TLS verify-full'),
        ('DB_SSLROOTCERT', 'relative.pem', 'TLS verify-full'),
        ('DB_HOST', 'postgres', 'external verified-TLS endpoint'),
        ('DB_HOST', '127.0.0.1', 'external verified-TLS endpoint'),
    ],
)
def test_production_migration_role_rejects_unverified_or_bundled_database(
    monkeypatch, name, value, message
):
    from api.settings import Settings

    required = {
        'ENV': 'production',
        'BASE2_PROCESS_ROLE': 'migration',
        'DB_HOST': 'private-db.example.test',
        'DB_SSLMODE': 'verify-full',
        'DB_SSLROOTCERT': '/run/secrets/database-ca.pem',
    }
    for key, configured in required.items():
        monkeypatch.setenv(key, configured)
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=message):
        Settings()


def test_production_migration_role_accepts_only_verified_external_database(monkeypatch):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('BASE2_PROCESS_ROLE', 'migration')
    monkeypatch.setenv('DB_HOST', 'private-db.example.test')
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/run/secrets/database-ca.pem')
    settings = Settings()
    assert settings.BASE2_PROCESS_ROLE == 'migration'
    assert settings.DB_HOST == 'private-db.example.test'


@pytest.mark.parametrize(
    'database_url',
    (
        'postgresql://owner:secret@postgres:5432/app',
        'postgresql://owner:secret@localhost:5432/app',
        'postgresql://owner:secret@localhost.:5432/app',
        'postgresql://owner:secret@%6cocalhost:5432/app',
        'postgresql://owner:secret@localhost%2e:5432/app',
        'postgresql://owner:secret@127%2e0%2e0%2e1:5432/app',
        'postgresql://owner:secret@%31%32%37.0.0.1:5432/app',
        'postgresql://owner:secret@%3a%3affff%3a127.0.0.1:5432/app',
        'postgresql://owner:secret@127.0.0.1:5432/app',
        'postgresql://owner:secret@[::1]:5432/app',
        'postgresql://owner:secret@[::ffff:127.0.0.1]:5432/app',
        'postgresql://owner:secret@0.0.0.0:5432/app',
        'postgresql://owner:secret@169.254.1.1:5432/app',
        'postgresql://owner:secret@10.0.0.1:5432/app',
        'postgresql:///app',
        'postgresql://owner:secret@[invalid/app',
        'sqlite:///tmp/app.db',
    ),
)
@pytest.mark.parametrize('role', ('api', 'runtime-worker', 'migration'))
def test_production_rejects_database_url_that_bypasses_effective_host(
    monkeypatch, database_url, role
):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('BASE2_PROCESS_ROLE', role)
    monkeypatch.setenv('DB_HOST', 'private-db.example.test')
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/run/secrets/database-ca.pem')
    monkeypatch.setenv('DATABASE_URL', database_url)
    with pytest.raises(RuntimeError):
        Settings()


def test_production_accepts_verified_external_database_url(monkeypatch):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('BASE2_PROCESS_ROLE', 'migration')
    monkeypatch.setenv('DB_HOST', 'ignored-local-validation.example.test')
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/run/secrets/database-ca.pem')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://owner:secret@private-db.example.test:5432/app')
    assert Settings().DATABASE_URL.endswith('/app')


@pytest.mark.parametrize(
    'database_host',
    (
        'localhost.',
        '%6cocalhost',
        'localhost%2e',
        '127%2e0%2e0%2e1',
        '%31%32%37.0.0.1',
        '%3a%3affff%3a127.0.0.1',
        '::1',
        '::ffff:127.0.0.1',
        '0.0.0.0',
        '169.254.1.1',
        '10.0.0.1',
    ),
)
@pytest.mark.parametrize('role', ('api', 'runtime-worker', 'migration'))
def test_production_rejects_canonical_local_database_host(monkeypatch, database_host, role):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('BASE2_PROCESS_ROLE', role)
    monkeypatch.setenv('DB_HOST', database_host)
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/run/secrets/database-ca.pem')
    monkeypatch.setenv('JWT_SECRET', 'fixture-jwt')
    monkeypatch.setenv('TOKEN_PEPPER', 'fixture-pepper-long-enough')
    monkeypatch.setenv('FRONTEND_URL', 'https://example.test')
    monkeypatch.setenv('OAUTH_STATE_SECRET', 'fixture-oauth-state')
    monkeypatch.setenv('IDENTITY_ENCRYPTION_KEY', 'fixture-identity-key')
    monkeypatch.setenv(
        'CONTENT_WORKSPACE_STORAGE_KEY', base64.urlsafe_b64encode(b'k' * 32).decode()
    )
    with pytest.raises(RuntimeError, match='external verified-TLS endpoint'):
        Settings()


def test_staging_s3_storage_requires_allowlisted_https_and_secret_files(monkeypatch):
    from api.settings import Settings

    required = {
        'ENV': 'staging',
        'JWT_SECRET': 'fixture-jwt',
        'TOKEN_PEPPER': 'fixture-pepper-long-enough',
        'IDENTITY_ENCRYPTION_KEY': 'fixture-identity',
        'FRONTEND_URL': 'https://example.test',
        'OAUTH_STATE_SECRET': 'fixture-state',
        'DB_SSLMODE': 'verify-full',
        'DB_SSLROOTCERT': '/run/secrets/database-ca.pem',
        'CONTENT_WORKSPACE_STORAGE_BACKEND': 's3',
        'CONTENT_WORKSPACE_S3_ENDPOINT': 'https://objects.example.net',
        'CONTENT_WORKSPACE_S3_BUCKET': 'base2-media',
        'CONTENT_WORKSPACE_S3_REGION': 'fra1',
        'CONTENT_WORKSPACE_S3_ALLOWED_HOSTS': 'objects.example.net',
        'CONTENT_WORKSPACE_S3_ACCESS_KEY_FILE': '/run/secrets/s3-access',
        'CONTENT_WORKSPACE_S3_SECRET_KEY_FILE': '/run/secrets/s3-secret',
    }
    monkeypatch.delenv('CONTENT_WORKSPACE_STORAGE_KEY', raising=False)
    for key, value in required.items():
        monkeypatch.setenv(key, value)
    assert Settings().CONTENT_WORKSPACE_STORAGE_BACKEND == 's3'
    monkeypatch.setenv('CONTENT_WORKSPACE_S3_ENDPOINT', 'http://objects.example.net')
    with pytest.raises(RuntimeError, match='S3 endpoint'):
        Settings()
    monkeypatch.setenv('CONTENT_WORKSPACE_S3_ENDPOINT', 'https://objects.example.net')
    monkeypatch.setenv('ENV', 'production')
    with pytest.raises(RuntimeError, match='Production S3 is disabled'):
        Settings()


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
        'BASE2_PROCESS_ROLE': 'runtime-worker',
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
    monkeypatch.setenv(
        'OPERATIONS_ALERT_WEBHOOK_URL_FILE', '/run/secrets/operations_alert_receipt_key_file'
    )
    with pytest.raises(RuntimeError, match='independently scoped'):
        Settings()


def test_only_production_email_worker_requires_or_receives_smtp_configuration(monkeypatch):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('BASE2_PROCESS_ROLE', 'runtime-worker')
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/run/secrets/database-ca.pem')
    monkeypatch.setenv('DB_HOST', 'private-db.example.test')
    monkeypatch.setenv('BASE2_EMAIL_ADAPTER', 'disabled')
    for name in (
        'BASE2_EMAIL_SMTP_HOST',
        'BASE2_EMAIL_FROM_ADDRESS',
        'BASE2_EMAIL_SMTP_USERNAME_FILE',
        'BASE2_EMAIL_SMTP_PASSWORD_FILE',
    ):
        monkeypatch.setenv(name, '')
    assert Settings().BASE2_PROCESS_ROLE == 'runtime-worker'

    monkeypatch.setenv('BASE2_PROCESS_ROLE', 'email-worker')
    with pytest.raises(RuntimeError, match='email worker requires'):
        Settings()


def test_data_rights_worker_requires_only_its_cryptographic_runtime_secrets(monkeypatch):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'staging')
    monkeypatch.setenv('BASE2_PROCESS_ROLE', 'data-rights-worker')
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/run/secrets/database-ca.pem')
    monkeypatch.delenv('IDENTITY_ENCRYPTION_KEY', raising=False)
    monkeypatch.delenv('TOKEN_PEPPER', raising=False)
    with pytest.raises(RuntimeError, match='IDENTITY_ENCRYPTION_KEY.*TOKEN_PEPPER'):
        Settings()
    monkeypatch.setenv('IDENTITY_ENCRYPTION_KEY', 'fixture-identity')
    monkeypatch.setenv('TOKEN_PEPPER', 'fixture-pepper')
    configured = Settings()
    assert configured.BASE2_PROCESS_ROLE == 'data-rights-worker'


@pytest.mark.parametrize('host', ('postgres', 'localhost', '127.0.0.1'))
def test_production_rejects_bundled_or_loopback_database(monkeypatch, host):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('BASE2_PROCESS_ROLE', 'runtime-worker')
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/run/secrets/database-ca.pem')
    monkeypatch.setenv('DB_HOST', host)
    with pytest.raises(RuntimeError, match='external verified-TLS endpoint'):
        Settings()


def test_production_docs_default_closed_but_allow_explicit_activation(monkeypatch):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('BASE2_PROCESS_ROLE', 'runtime-worker')
    monkeypatch.setenv('DB_SSLMODE', 'verify-full')
    monkeypatch.setenv('DB_SSLROOTCERT', '/run/secrets/database-ca.pem')
    monkeypatch.setenv('DB_HOST', 'private-db.example.test')
    monkeypatch.delenv('API_DOCS_ENABLED', raising=False)
    assert Settings().API_DOCS_ENABLED is False
    monkeypatch.setenv('API_DOCS_ENABLED', 'true')
    assert Settings().API_DOCS_ENABLED is True
