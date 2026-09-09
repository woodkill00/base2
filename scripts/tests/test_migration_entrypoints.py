from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_supported_migration_entrypoints_run_api_before_django_and_fail_hard():
    bash = (ROOT / "scripts/bash/migrate.sh").read_text(encoding="utf-8")
    powershell = (ROOT / "scripts/powershell/migrate.ps1").read_text(encoding="utf-8")
    for source in (bash, powershell):
        role = source.index("workspace-db-role")
        api = source.index("api-migrate python -m api.scripts.migrate")
        django = source.index("django python manage.py migrate")
        assert role < api < django
        assert "--no-deps" in source
        assert "api python -m api.scripts.migrate" not in source
    assert "exec -T django python manage.py migrate" not in bash
    assert powershell.count("if ($LASTEXITCODE -ne 0)") == 3


def test_migration_service_is_owner_scoped_and_not_part_of_default_runtime():
    for name in ("local.docker.yml", "development.docker.yml"):
        source = (ROOT / name).read_text(encoding="utf-8")
        block = source.split("  api-migrate:\n", 1)[1].split("\n  # Django", 1)[0]
        assert "profiles: [tools]" in block
        assert "DB_USER=${POSTGRES_USER}" in block
        assert "DB_PASSWORD=${POSTGRES_PASSWORD}" in block
        assert "BASE2_PROCESS_ROLE=migration" in block
        assert "workspace-db-role" in block


def test_remote_verification_checks_migrations_without_mutating_or_suppressing_failure():
    source = (
        ROOT / "digital_ocean/scripts/bash/remote_verify_min.sh"
    ).read_text(encoding="utf-8")
    api = "api python -m api.scripts.migrate --check"
    django = "django python manage.py migrate --check --noinput"
    assert source.index(api) < source.index(django)
    assert f"{api} > /root/logs/api-migrate-check.txt 2>&1" in source
    assert f"{django} > /root/logs/django-migrate.txt 2>&1" in source
    assert "curl -sk" not in source
    assert "manage.py migrate --noinput" not in source
