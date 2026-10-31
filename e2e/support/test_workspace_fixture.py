"""Pure guard tests; never connect to Docker, a database, or a browser."""

import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).with_name("workspace_fixture.py")
spec = importlib.util.spec_from_file_location("workspace_fixture", path)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def environment(monkeypatch, *, seed=False):
    for key, value in {
        "ENV": "test",
        "E2E_WORKSPACE_DISPOSABLE": "1",
        "DB_HOST": "postgres",
        "DB_NAME": "e2e",
        "DB_PORT": "5432",
        "WORKSPACE_WORKER_DB_USER": "base2_workspace_worker_e2e",
        "CONTENT_WORKSPACE_STORAGE_BACKEND": "local",
        "CONTENT_WORKSPACE_STORAGE_ROOT": "/var/lib/base2/content-workspace",
        "SITE_PROFILE": "base2-obsidian",
        "DB_USER": "e2e" if seed else "base2_workspace_worker_e2e",
        "BASE2_PROCESS_ROLE": "migration" if seed else "content-worker",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("DATABASE_URL", raising=False)


@pytest.mark.parametrize(
    "key,value",
    [
        ("ENV", "production"),
        ("DB_HOST", "external"),
        ("DB_NAME", "real"),
        ("SITE_PROFILE", "other-site"),
        ("E2E_WORKSPACE_DISPOSABLE", "0"),
        ("DATABASE_URL", "postgres://remote"),
        ("DB_USER", "postgres"),
        ("WORKSPACE_WORKER_DB_USER", "e2e"),
        ("DB_PORT", "5433"),
    ],
)
def test_disposable_guard_fails_closed(monkeypatch, key, value):
    environment(monkeypatch)
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match="disposable"):
        fixture.guard(seed=False)


def test_seed_and_worker_credentials_cannot_be_interchanged(monkeypatch):
    environment(monkeypatch, seed=True)
    fixture.guard(seed=True)
    with pytest.raises(RuntimeError):
        fixture.guard(seed=False)
    environment(monkeypatch)
    fixture.guard(seed=False)
    with pytest.raises(RuntimeError):
        fixture.guard(seed=True)


def test_control_clock_requires_explicit_utc_and_bounded_window():
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    assert fixture.control_clock((now + timedelta(days=1)).isoformat()).tzinfo is not None
    for value in [
        "2020-01-01",
        "2020-01-01T00:00:00Z",
        now.replace(tzinfo=None).isoformat(),
        (now + timedelta(days=3)).isoformat(),
    ]:
        with pytest.raises(ValueError):
            fixture.control_clock(value)


def test_cli_never_accepts_tenant_role_sql_or_snapshot_clock():
    for args in [
        ("snapshot", "--site", "foreign"),
        ("snapshot", "--sql", "SELECT 1"),
        ("snapshot", "--role", "owner"),
        ("snapshot", "--now", "2026-01-01"),
        ("suspend-viewer", "--user-id", fixture.ACTORS["owner"]),
        ("suspend-viewer", "--site", "foreign"),
    ]:
        with pytest.raises(SystemExit) as exc:
            fixture.main(args)
        assert exc.value.code == 2


def test_seed_rejects_remote_storage_before_import_or_connection(monkeypatch):
    environment(monkeypatch, seed=True)
    monkeypatch.setenv("CONTENT_WORKSPACE_STORAGE_BACKEND", "s3")
    with pytest.raises(RuntimeError, match="disposable"):
        fixture.seed()


def test_owned_fixture_validation_requires_exact_synthetic_organization_and_identities():
    organization = (fixture.ORG, fixture.SITE, "Disposable workspace acceptance")
    users = [
        (value, fixture.identities()["actors"][name]["email"])
        for name, value in fixture.ACTORS.items()
    ]
    fixture.validate_owned_fixture(organization, users)
    for bad_org, bad_users in [
        (None, users),
        ((fixture.ORG, "other", organization[2]), users),
        (organization, users[:-1]),
        (organization, users + [users[0]]),
        (organization, [(users[0][0], "real@example.com"), *users[1:]]),
    ]:
        with pytest.raises(RuntimeError, match="ownership"):
            fixture.validate_owned_fixture(bad_org, bad_users)


def test_suspend_command_cannot_run_with_worker_credentials(monkeypatch):
    environment(monkeypatch)
    with pytest.raises(RuntimeError, match="disposable"):
        fixture.suspend_viewer()
