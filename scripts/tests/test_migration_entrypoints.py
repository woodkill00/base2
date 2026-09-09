from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_supported_migration_entrypoints_run_api_before_django_and_fail_hard():
    bash = (ROOT / "scripts/bash/migrate.sh").read_text(encoding="utf-8")
    powershell = (ROOT / "scripts/powershell/migrate.ps1").read_text(encoding="utf-8")
    for source in (bash, powershell):
        api = source.index("api python -m api.scripts.migrate")
        django = source.index("django python manage.py migrate")
        assert api < django
        assert "--no-deps" in source
    assert "exec -T django python manage.py migrate" not in bash
    assert powershell.count("if ($LASTEXITCODE -ne 0)") == 2


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
