import os
import subprocess
import sys


def _load_settings(**overrides):
    environment = {
        **os.environ,
        "ENV": "production",
        "DJANGO_SECRET_KEY": "synthetic-production-settings-key",
        "DB_NAME": "base2",
        "DB_USER": "base2",
        "DB_PASSWORD": "synthetic-password",
        "DB_HOST": "managed-db.example.invalid",
        "DB_SSLMODE": "verify-full",
        "DB_SSLROOTCERT": "/run/secrets/database-ca.crt",
        **overrides,
    }
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from project.settings.base import DATABASES; "
            "print(DATABASES['default']['HOST']); "
            "print(DATABASES['default']['OPTIONS']['sslmode']); "
            "print(DATABASES['default']['OPTIONS']['sslrootcert'])",
        ],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_django_database_requires_external_hostname_verified_tls():
    accepted = _load_settings()
    assert accepted.returncode == 0, accepted.stderr
    assert accepted.stdout.splitlines() == [
        "managed-db.example.invalid",
        "verify-full",
        "/run/secrets/database-ca.crt",
    ]
    for overrides, error in (
        ({"DB_SSLMODE": "disable"}, "production_database_verified_tls_required"),
        ({"DB_SSLMODE": "require"}, "production_database_verified_tls_required"),
        ({"DB_SSLROOTCERT": ""}, "production_database_verified_tls_required"),
        ({"DB_HOST": "postgres"}, "production_external_database_required"),
        ({"DB_HOST": "127.0.0.1"}, "production_external_database_required"),
    ):
        rejected = _load_settings(**overrides)
        assert rejected.returncode != 0
        assert error in rejected.stderr
