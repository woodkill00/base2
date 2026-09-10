import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet

from api.security.secret_box import SecretBox
from api.services import data_rights_worker as worker


USER_ID = UUID('00000000-0000-0000-0000-000000000801')
OPERATION_ID = UUID('00000000-0000-0000-0000-000000000802')
DISPATCH_TOKEN = UUID('00000000-0000-0000-0000-000000000803')


def _operation(kind, key, payload):
    return {
        'id': OPERATION_ID,
        'tenant_id': 'tenant-a',
        'user_id': USER_ID,
        'kind': kind,
        'request_ciphertext': SecretBox(key).encrypt(json.dumps(payload)),
        'claim_token': uuid4(),
    }


@pytest.mark.parametrize(
    ('kind', 'request_payload', 'expected_key'),
    (
        ('export', {'schema_version': 1}, 'account'),
        ('correction', {'fields': {'display_name': 'New Name'}}, 'corrected'),
        ('deactivation', {'confirmation': 'DEACTIVATE'}, 'deactivated'),
        ('deletion', {'confirmation': 'DELETE'}, 'deleted'),
    ),
)
def test_worker_completes_exact_supported_operation(
    monkeypatch, kind, request_payload, expected_key
):
    key = Fernet.generate_key().decode('ascii')
    captured = {}
    monkeypatch.setattr(worker.settings, 'IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr(worker.settings, 'TOKEN_PEPPER', 'pepper')
    monkeypatch.setattr(
        worker.repository,
        'claim_operation',
        lambda **kwargs: _operation(kind, key, request_payload),
    )
    monkeypatch.setattr(
        worker,
        '_export_payload',
        lambda **kwargs: {'schema_version': 1, 'account': {'email': 'owner@example.test'}},
    )
    monkeypatch.setattr(worker, '_correct_account', lambda **kwargs: USER_ID)
    monkeypatch.setattr(
        worker,
        '_workspace_payload',
        lambda **kwargs: {'schema_version': 1, 'records': []},
    )
    monkeypatch.setattr(
        worker,
        '_delete_account',
        lambda **kwargs: {'schema_version': 1, 'deleted': True, 'tenant_id': 'tenant-a'},
    )
    monkeypatch.setattr(
        worker,
        '_deactivate_account',
        lambda **kwargs: {'schema_version': 1, 'deactivated': True, 'tenant_id': 'tenant-a'},
    )
    monkeypatch.setattr(
        worker.repository, 'complete_operation', lambda **kwargs: captured.update(kwargs)
    )
    monkeypatch.setattr(worker.repository, 'fail_operation', lambda **kwargs: pytest.fail('failed'))
    assert worker.process_operation(OPERATION_ID, DISPATCH_TOKEN) == 'completed'
    result = json.loads(SecretBox(key).decrypt(captured['result_ciphertext']))
    assert expected_key in result
    assert captured['digest'] and len(captured['digest']) == 64


def test_worker_noops_claimed_replay_and_records_generic_failure(monkeypatch):
    monkeypatch.setattr(worker.repository, 'claim_operation', lambda **kwargs: None)
    assert worker.process_operation(OPERATION_ID, DISPATCH_TOKEN) == 'noop'

    key = Fernet.generate_key().decode('ascii')
    failures = []
    monkeypatch.setattr(worker.settings, 'IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr(
        worker.repository,
        'claim_operation',
        lambda **kwargs: _operation('unsupported', key, {'secret': 'never-log'}),
    )
    monkeypatch.setattr(
        worker.repository, 'fail_operation', lambda **kwargs: failures.append(kwargs)
    )
    with pytest.raises(ValueError, match='operation_kind_invalid'):
        worker.process_operation(OPERATION_ID, DISPATCH_TOKEN)
    assert failures[0]['operation_id'] == OPERATION_ID
    assert failures[0]['error_code'] == 'processing_failed'
    assert failures[0]['claim_token']


def test_export_timestamp_serialization_is_explicit(monkeypatch):
    class Cursor:
        def __init__(self):
            self.query = ''

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, _params):
            self.query = query

        def fetchone(self):
            now = datetime(2026, 8, 25, tzinfo=timezone.utc)
            return ('owner@example.test', True, True, 'Owner', '', '', now, now)

        def fetchall(self):
            return []

    class Connection:
        def set_session(self, **kwargs):
            assert kwargs == {'isolation_level': 'REPEATABLE READ', 'readonly': True}

        def cursor(self):
            return Cursor()

    class Context:
        def __enter__(self):
            return Connection()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(worker, 'db_conn', lambda **kwargs: Context())
    monkeypatch.setattr(
        worker,
        '_workspace_payload',
        lambda **kwargs: {'schema_version': 1, 'records': []},
    )
    payload = worker._export_payload(tenant_id='tenant-a', user_id=USER_ID)
    assert payload['account']['created_at'] == '2026-08-25T00:00:00+00:00'
    assert payload['memberships'] == []
    assert payload['workspace']['schema_version'] == 3
    assert payload['workspace']['records'] == []
    assert payload['authenticators'] == []
    assert payload['credentials'] == []
    assert payload['audit_events'] == []
    assert payload['workspace']['subject_surfaces'] == []


def test_workspace_privacy_projection_is_tenant_subject_and_field_permission_bound():
    record_id = UUID(int=9104)
    definition_id = UUID(int=9105)

    class Cursor:
        def __init__(self):
            self.calls = []
            self.results = [
                [
                    (
                        record_id,
                        'article',
                        'safe',
                        'Safe',
                        'draft',
                        2,
                        3,
                        {'public_name': 'Shown', 'private_note': 'Never export'},
                        definition_id,
                    )
                ],
                [(definition_id, 'public_name')],
            ]

        def execute(self, query, params):
            self.calls.append((' '.join(query.split()), params))

        def fetchall(self):
            return self.results.pop(0) if self.results else []

    cursor = Cursor()
    projection = worker._workspace_projection(cursor, tenant_id='tenant-a', user_id=USER_ID)
    assert projection['records'][0]['values'] == {'public_name': 'Shown'}
    assert 'private_note' not in json.dumps(projection)
    assert cursor.calls[0][1] == ('tenant-a', 'tenant-a', str(USER_ID))
    assert "a.action='content.create'" in cursor.calls[0][0]
    assert "read_permission='content.read'" in cursor.calls[1][0]


def test_workspace_subject_rows_include_values_but_strip_private_storage_fields():
    safe = worker._privacy_safe_row(
        {
            'id': USER_ID,
            'title': 'Owned item',
            'storage_key': 'private/object',
            'secret_ciphertext': 'never-export',
        }
    )
    assert safe['id'] == USER_ID
    assert safe['title'] == 'Owned item'
    assert 'storage_key' not in safe and 'secret_ciphertext' not in safe


def test_deactivation_uses_only_the_fixed_claim_bound_repository_action(monkeypatch):
    claim = UUID(int=803)
    calls = []
    monkeypatch.setattr(
        worker.repository,
        'apply_subject_action',
        lambda **kwargs: calls.append(kwargs)
        or {
            'tenant_membership_deactivated': True,
            'global_account_deactivated': False,
            'tenant_id': 'tenant-a',
        },
    )
    result = worker._deactivate_account(operation_id=OPERATION_ID, claim_token=claim)
    assert result['tenant_membership_deactivated'] is True
    assert result['global_account_deactivated'] is False
    assert calls == [
        {'operation_id': OPERATION_ID, 'claim_token': claim, 'action': 'deactivation'}
    ]


def test_subject_inventory_is_database_registered_and_claim_fenced():
    source = Path(worker.__file__).read_text(encoding='utf-8')
    assert 'base2_export_data_rights_subject_surfaces()' in source
    assert 'SUBJECT_DATA_INVENTORY = (' not in source


@pytest.mark.parametrize('operation', ['deletion', 'deactivation'])
def test_tenant_only_closure_preserves_global_identity_when_another_membership_is_active(
    monkeypatch, operation
):
    claim = UUID(int=804)
    key = f'global_account_{"deleted" if operation == "deletion" else "deactivated"}'
    monkeypatch.setattr(
        worker.repository,
        'apply_subject_action',
        lambda **_kwargs: {
            f'tenant_membership_{"deleted" if operation == "deletion" else "deactivated"}': True,
            key: False,
            'tenant_id': 'tenant-a',
        },
    )
    if operation == 'deletion':
        monkeypatch.setattr(worker, '_workspace_payload', lambda **_kwargs: {'records': []})
        result = worker._delete_account(
            operation_id=OPERATION_ID, claim_token=claim,
            tenant_id='tenant-a', user_id=USER_ID
        )
        assert result['global_account_deleted'] is False
    else:
        result = worker._deactivate_account(operation_id=OPERATION_ID, claim_token=claim)
        assert result['global_account_deactivated'] is False
