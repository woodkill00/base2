from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import app
from api.migrations.runner import MIGRATIONS
from api.routes.settings import NotificationChoice, PreferenceUpdate, _notification_payload
from api.routes.users import _safe_avatar_url


def valid_preferences(**overrides):
    values = {
        'expected_version': 0,
        'theme': 'system',
        'contrast': 'system',
        'motion': 'system',
        'density': 'comfortable',
        'locale': 'en',
        'timezone': 'UTC',
        'week_start': 'system',
    }
    values.update(overrides)
    return values


def test_preferences_are_closed_typed_and_versioned():
    payload = PreferenceUpdate.model_validate(valid_preferences(theme='dark'))
    assert payload.theme == 'dark'
    with pytest.raises(ValidationError):
        PreferenceUpdate.model_validate(valid_preferences(unexpected='unsafe'))
    with pytest.raises(ValidationError):
        PreferenceUpdate.model_validate(valid_preferences(theme='unknown'))
    with pytest.raises(ValidationError):
        PreferenceUpdate.model_validate(valid_preferences(expected_version=-1))


def test_notifications_reject_duplicates_and_disabled_mandatory_delivery():
    product = NotificationChoice(event_family='product', channel='email', delivery='digest')
    assert _notification_payload([product])[0]['mandatory'] is False
    with pytest.raises(HTTPException, match='settings_notification_duplicate'):
        _notification_payload([product, product])
    security = NotificationChoice(event_family='security', channel='email', delivery='disabled')
    with pytest.raises(HTTPException, match='settings_notification_mandatory'):
        _notification_payload([security])


@pytest.mark.parametrize('value', [
    'http://example.com/a.png',
    'https://user:pass@example.com/a.png',
    'https://localhost/a.png',
    'https://127.0.0.1/a.png',
    'https://10.0.0.1/a.png',
    'https://169.254.169.254/latest/meta-data',
])
def test_avatar_url_rejects_unsafe_origins(value):
    with pytest.raises(ValueError, match='avatar_url_invalid'):
        _safe_avatar_url(value)


def test_avatar_url_allows_empty_or_public_https_without_fetching():
    assert _safe_avatar_url('') == ''
    assert _safe_avatar_url(None) is None
    assert _safe_avatar_url('https://cdn.example.com/avatar.png') == 'https://cdn.example.com/avatar.png'


def test_django_and_api_settings_schema_contracts_exist():
    root = Path(__file__).resolve().parents[2]
    django_migration = (root / 'django/users/migrations/0008_notificationpreference_userpreferenceset.py').read_text()
    api_migration = (root / 'api/migrations/sql/008_create_settings_tables.sql').read_text()
    for token in ('theme', 'contrast', 'motion', 'density', 'locale', 'timezone', 'week_start'):
        assert token in django_migration
        assert token in api_migration
    assert 'UNIQUE (user_id, tenant_id)' in api_migration
    assert "CHECK (NOT mandatory OR delivery <> 'disabled')" in api_migration


def test_api_migration_runner_executes_every_checked_in_sql_migration_in_order():
    root = Path(__file__).resolve().parents[2]
    checked_in = tuple(path.stem for path in sorted((root / 'api/migrations/sql').glob('*.sql')))
    assert MIGRATIONS == checked_in
    assert MIGRATIONS[-2:] == ('008_create_settings_tables', '009_add_deactivation_operation')


def _admit_settings(monkeypatch):
    principal = SimpleNamespace(user_id=UUID('00000000-0000-0000-0000-000000001103'))
    monkeypatch.setattr('api.routes.settings.require_authenticated_principal', lambda request: principal)
    monkeypatch.setattr('api.routes.settings.require_tenant', lambda request: 'tenant-a')
    return principal


def test_preferences_endpoint_is_tenant_bound_audited_and_conflict_safe(monkeypatch):
    principal = _admit_settings(monkeypatch)
    captured = {}
    monkeypatch.setattr('api.routes.settings.repository.update_preferences', lambda **kwargs: captured.update(kwargs) or {**valid_preferences(), 'version': 1})
    monkeypatch.setattr('api.routes.settings.insert_audit_event', lambda **kwargs: captured.setdefault('audit', kwargs))
    response = TestClient(app).put('/api/settings/preferences', json=valid_preferences())
    assert response.status_code == 200, response.text
    assert captured['user_id'] == principal.user_id
    assert captured['tenant_id'] == 'tenant-a'
    assert captured['audit']['action'] == 'user.preferences_updated'
    assert captured['audit']['metadata'] == {'tenant_id': 'tenant-a', 'version': 1}

    monkeypatch.setattr('api.routes.settings.repository.update_preferences', lambda **kwargs: None)
    conflict = TestClient(app).put('/api/settings/preferences', json=valid_preferences())
    assert conflict.status_code == 409
    assert conflict.json() == {'detail': 'settings_version_conflict'}


def test_preferences_reject_invalid_locale_timezone_and_unknown_fields_before_write(monkeypatch):
    _admit_settings(monkeypatch)
    writes = []
    monkeypatch.setattr('api.routes.settings.repository.update_preferences', lambda **kwargs: writes.append(kwargs))
    invalid_locale = TestClient(app).put('/api/settings/preferences', json=valid_preferences(locale='xx-invalid'))
    invalid_timezone = TestClient(app).put('/api/settings/preferences', json=valid_preferences(timezone='Not/AZone'))
    unknown = TestClient(app).put('/api/settings/preferences', json=valid_preferences(secret='no'))
    assert invalid_locale.status_code == invalid_timezone.status_code == unknown.status_code == 422
    assert writes == []


def test_notification_endpoint_preserves_required_families_and_audits_exact_count(monkeypatch):
    _admit_settings(monkeypatch)
    captured = {}
    monkeypatch.setattr('api.routes.settings.repository.replace_notifications', lambda **kwargs: captured.update(kwargs) or kwargs['preferences'])
    monkeypatch.setattr('api.routes.settings.insert_audit_event', lambda **kwargs: captured.setdefault('audit', kwargs))
    payload = {'preferences': [
        {'event_family': 'security', 'channel': 'email', 'delivery': 'immediate'},
        {'event_family': 'marketing', 'channel': 'email', 'delivery': 'disabled'},
    ]}
    response = TestClient(app).put('/api/settings/notifications', json=payload)
    assert response.status_code == 200, response.text
    assert captured['tenant_id'] == 'tenant-a'
    assert captured['preferences'][0]['mandatory'] is True
    assert captured['preferences'][1]['mandatory'] is False
    assert captured['audit']['metadata']['preference_count'] == 2

    payload['preferences'][0]['delivery'] = 'disabled'
    denied = TestClient(app).put('/api/settings/notifications', json=payload)
    assert denied.status_code == 422
    assert denied.json() == {'detail': 'settings_notification_mandatory'}


def test_capability_contract_uses_closed_known_category_ids(monkeypatch):
    _admit_settings(monkeypatch)
    response = TestClient(app).get('/api/settings/capabilities')
    assert response.status_code == 200
    body = response.json()
    assert body['schema_version'] == 1
    assert [item['id'] for item in body['categories']] == [
        'overview', 'profile', 'security', 'privacy', 'notifications', 'appearance',
        'language-region',
    ]
    monkeypatch.setattr('api.routes.settings._accounts_enabled', lambda: True)
    enabled = TestClient(app).get('/api/settings/capabilities').json()
    assert [item['id'] for item in enabled['categories']][-2:] == ['organization', 'developer']
