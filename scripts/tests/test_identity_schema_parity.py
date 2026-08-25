import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_SQL = ROOT / 'api/migrations/sql/005_create_identity_admin_tables.sql'
DJANGO_MIGRATION = ROOT / 'django/api_schema/migrations/0002_identity_admin_tables.py'
DATA_RIGHTS_SQL = ROOT / 'api/migrations/sql/006_create_data_rights_operations.sql'
DATA_RIGHTS_DJANGO = ROOT / 'django/api_schema/migrations/0003_data_rights_operations.py'


def _names(pattern: str, text: str) -> set[str]:
    return set(re.findall(pattern, text, flags=re.IGNORECASE))


def test_api_compatibility_sql_and_django_owner_migration_have_schema_parity():
    api_sql = API_SQL.read_text(encoding='utf-8')
    django = DJANGO_MIGRATION.read_text(encoding='utf-8')
    table_pattern = r'CREATE TABLE IF NOT EXISTS\s+(api_identity_[a-z_]+)'
    index_pattern = r'CREATE INDEX IF NOT EXISTS\s+(api_identity_[a-z_]+)'
    assert _names(table_pattern, api_sql) == _names(table_pattern, django)
    assert _names(index_pattern, api_sql) == _names(index_pattern, django)
    assert _names(table_pattern, api_sql) == {
        'api_identity_authenticators',
        'api_identity_credentials',
        'api_identity_invitations',
        'api_identity_login_challenges',
        'api_identity_memberships',
        'api_identity_organizations',
        'api_identity_recovery_codes',
    }


def test_django_reverse_removes_every_identity_table_in_dependency_order():
    django = DJANGO_MIGRATION.read_text(encoding='utf-8')
    created = _names(r'CREATE TABLE IF NOT EXISTS\s+(api_identity_[a-z_]+)', django)
    dropped = _names(r'DROP TABLE IF EXISTS\s+(api_identity_[a-z_]+)', django)
    assert dropped == created
    assert django.index('DROP TABLE IF EXISTS api_identity_memberships') < django.index(
        'DROP TABLE IF EXISTS api_identity_organizations'
    )


def test_data_rights_api_and_django_migrations_have_table_and_index_parity():
    api_sql = DATA_RIGHTS_SQL.read_text(encoding='utf-8')
    django = DATA_RIGHTS_DJANGO.read_text(encoding='utf-8')
    table_pattern = r'CREATE TABLE IF NOT EXISTS\s+(api_data_rights_[a-z_]+)'
    index_pattern = r'CREATE (?:UNIQUE )?INDEX IF NOT EXISTS\s+(api_data_rights_[a-z_]+)'
    assert _names(table_pattern, api_sql) == _names(table_pattern, django) == {
        'api_data_rights_operations'
    }
    assert _names(index_pattern, api_sql) == _names(index_pattern, django) == {
        'api_data_rights_active_kind_idx',
        'api_data_rights_owner_idx',
        'api_data_rights_retention_idx',
    }
    assert "WHERE status IN ('queued', 'running')" in api_sql
    assert "WHERE status IN ('queued', 'running')" in django
    assert 'DROP TABLE IF EXISTS api_data_rights_operations' in django
