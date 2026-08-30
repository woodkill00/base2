import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from cryptography.fernet import Fernet

from api.security.secret_box import SecretBox
from api.services import data_rights_worker as worker


USER_ID = UUID('00000000-0000-0000-0000-000000000801')
OPERATION_ID = UUID('00000000-0000-0000-0000-000000000802')


def _operation(kind, key, payload):
    return {
        'id': OPERATION_ID, 'tenant_id': 'tenant-a', 'user_id': USER_ID, 'kind': kind,
        'request_ciphertext': SecretBox(key).encrypt(json.dumps(payload)),
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
def test_worker_completes_exact_supported_operation(monkeypatch, kind, request_payload, expected_key):
    key = Fernet.generate_key().decode('ascii')
    captured = {}
    monkeypatch.setattr(worker.settings, 'IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr(worker.settings, 'TOKEN_PEPPER', 'pepper')
    monkeypatch.setattr(
        worker.repository, 'claim_operation',
        lambda **kwargs: _operation(kind, key, request_payload),
    )
    monkeypatch.setattr(
        worker, '_export_payload',
        lambda **kwargs: {'schema_version': 1, 'account': {'email': 'owner@example.test'}},
    )
    monkeypatch.setattr(
        worker, 'update_profile',
        lambda **kwargs: SimpleNamespace(id=USER_ID),
    )
    monkeypatch.setattr(
        worker, '_delete_account',
        lambda **kwargs: {'schema_version': 1, 'deleted': True, 'tenant_id': 'tenant-a'},
    )
    monkeypatch.setattr(
        worker, '_deactivate_account',
        lambda **kwargs: {'schema_version': 1, 'deactivated': True, 'tenant_id': 'tenant-a'},
    )
    monkeypatch.setattr(
        worker.repository, 'complete_operation', lambda **kwargs: captured.update(kwargs)
    )
    monkeypatch.setattr(worker.repository, 'fail_operation', lambda **kwargs: pytest.fail('failed'))
    monkeypatch.setattr(worker, 'insert_audit_event', lambda **kwargs: None)
    assert worker.process_operation(OPERATION_ID) == 'completed'
    result = json.loads(SecretBox(key).decrypt(captured['result_ciphertext']))
    assert expected_key in result
    assert captured['digest'] and len(captured['digest']) == 64


def test_worker_noops_claimed_replay_and_records_generic_failure(monkeypatch):
    monkeypatch.setattr(worker.repository, 'claim_operation', lambda **kwargs: None)
    assert worker.process_operation(OPERATION_ID) == 'noop'

    key = Fernet.generate_key().decode('ascii')
    failures = []
    monkeypatch.setattr(worker.settings, 'IDENTITY_ENCRYPTION_KEY', key)
    monkeypatch.setattr(
        worker.repository, 'claim_operation',
        lambda **kwargs: _operation('unsupported', key, {'secret': 'never-log'}),
    )
    monkeypatch.setattr(
        worker.repository, 'fail_operation', lambda **kwargs: failures.append(kwargs)
    )
    with pytest.raises(ValueError, match='operation_kind_invalid'):
        worker.process_operation(OPERATION_ID)
    assert failures == [{'operation_id': OPERATION_ID, 'error_code': 'processing_failed'}]


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
        def cursor(self):
            return Cursor()

    class Context:
        def __enter__(self):
            return Connection()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(worker, 'db_conn', lambda **kwargs: Context())
    payload = worker._export_payload(tenant_id='tenant-a', user_id=USER_ID)
    assert payload['account']['created_at'] == '2026-08-25T00:00:00+00:00'
    assert payload['memberships'] == []


def test_deactivation_fails_closed_for_final_owner_before_account_mutation(monkeypatch):
    class Cursor:
        rowcount = 1
        calls = []
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def execute(self, query, params): self.calls.append((' '.join(query.split()), params))
        def fetchone(self): return ('organization-a',)

    class Connection:
        def __init__(self): self.value = Cursor(); self.rollbacks = 0; self.commits = 0
        def cursor(self): return self.value
        def rollback(self): self.rollbacks += 1
        def commit(self): self.commits += 1

    connection = Connection()
    class Context:
        def __enter__(self): return connection
        def __exit__(self, *_args): return False
    monkeypatch.setattr(worker, 'db_conn', lambda **kwargs: Context())
    with pytest.raises(ValueError, match='last_owner_required'):
        worker._deactivate_account(tenant_id='tenant-a', user_id=USER_ID)
    assert connection.rollbacks == 1 and connection.commits == 0
    assert len(connection.value.calls) == 1
    assert 'UPDATE api_auth_users' not in connection.value.calls[0][0]


def test_deactivation_revokes_sessions_suspends_memberships_and_commits_atomically(monkeypatch):
    class Cursor:
        rowcount = 1
        def __init__(self): self.calls = []
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def execute(self, query, params): self.calls.append((' '.join(query.split()), params))
        def fetchone(self): return None

    class Connection:
        def __init__(self): self.value = Cursor(); self.rollbacks = 0; self.commits = 0
        def cursor(self): return self.value
        def rollback(self): self.rollbacks += 1
        def commit(self): self.commits += 1

    connection = Connection()
    class Context:
        def __enter__(self): return connection
        def __exit__(self, *_args): return False
    monkeypatch.setattr(worker, 'db_conn', lambda **kwargs: Context())
    result = worker._deactivate_account(tenant_id='tenant-a', user_id=USER_ID)
    assert result == {'schema_version': 1, 'deactivated': True, 'tenant_id': 'tenant-a'}
    assert connection.commits == 1 and connection.rollbacks == 0
    statements = ' '.join(query for query, _ in connection.value.calls)
    assert 'api_auth_refresh_tokens' in statements
    assert "status='suspended'" in statements
    assert 'is_active=FALSE' in statements
