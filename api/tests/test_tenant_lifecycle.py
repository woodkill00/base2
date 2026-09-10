import pytest
from fastapi.testclient import TestClient

from api.main import app
import base64
from unittest.mock import patch
from uuid import UUID

from datetime import UTC, datetime, timedelta

from api.services.tenant_lifecycle import (
    TenantLifecycleError,
    authorize,
    create_deletion_approval,
    identity_recovery,
    quota_state,
    quota_report,
    reconcile_quota,
    reserve_quota,
    session_action,
    settings_change,
    settle_quota,
    tenant_operation,
    transition_tenant,
    persist_operation,
    persist_provision,
    persist_transition,
    read_approval_key_file,
)

NOW = datetime(2026, 9, 8, tzinfo=UTC)
APPROVAL_KEY = b'd' * 32


def limits(value=10):
    return {
        name: value
        for name in ('users', 'storage', 'media', 'api', 'jobs', 'email', 'search', 'cost')
    }


def test_suspend_and_archive_remove_authority_without_deleting_data():
    suspended = transition_tenant(tenant_id='tenant-one', current='active', target='suspended')
    assert suspended['servingAuthority'] is False
    assert suspended['allocationAuthority'] is False
    assert suspended['recoverableDataPreserved'] is True
    archived = transition_tenant(tenant_id='tenant-one', current='suspended', target='archived')
    assert archived['recoverableDataPreserved'] is True


def test_deletion_is_separately_approved_and_irreversible():
    with pytest.raises(TenantLifecycleError, match='deletion_approval'):
        transition_tenant(tenant_id='tenant-one', current='archived', target='deleting')
    start = create_deletion_approval(
        tenant_id='tenant-one',
        current='archived',
        target='deleting',
        owner='owner-one',
        revision=1,
        expires_at=NOW + timedelta(minutes=10),
        nonce='delete-start-0001',
        key=APPROVAL_KEY,
    )
    consumed = set()

    def consume(tenant_id, nonce, approval_digest, expires_at):
        del tenant_id, approval_digest, expires_at
        if nonce in consumed:
            return False
        consumed.add(nonce)
        return True

    deleting = transition_tenant(
        tenant_id='tenant-one',
        current='archived',
        target='deleting',
        deletion_approval=start,
        now=NOW,
        approval_key=APPROVAL_KEY,
        expected_revision=1,
        consume_nonce=consume,
    )
    final = create_deletion_approval(
        tenant_id='tenant-one',
        current='deleting',
        target='deleted',
        owner='owner-one',
        revision=2,
        expires_at=NOW + timedelta(minutes=10),
        nonce='delete-final-0001',
        key=APPROVAL_KEY,
    )
    deleted = transition_tenant(
        tenant_id='tenant-one',
        current='deleting',
        target='deleted',
        deletion_approval=final,
        now=NOW,
        approval_key=APPROVAL_KEY,
        expected_revision=2,
        consume_nonce=consume,
    )
    assert deleting['recoverableDataPreserved'] is True
    assert deleted['recoverableDataPreserved'] is None
    assert deleted['dataDeletionVerified'] is False
    assert deleted['deletionVerificationRequired'] is True
    with pytest.raises(TenantLifecycleError):
        transition_tenant(tenant_id='tenant-one', current='deleted', target='active')
    with pytest.raises(TenantLifecycleError, match='approval_invalid'):
        transition_tenant(
            tenant_id='tenant-two',
            current='archived',
            target='deleting',
            deletion_approval=start,
            now=NOW,
            approval_key=APPROVAL_KEY,
            expected_revision=1,
            consume_nonce=lambda *_: True,
        )
    with pytest.raises(TenantLifecycleError, match='approval_invalid'):
        transition_tenant(
            tenant_id='tenant-one',
            current='archived',
            target='deleting',
            deletion_approval=start,
            now=NOW,
            approval_key=APPROVAL_KEY,
            expected_revision=1,
            consume_nonce=consume,
        )

    long_lived = create_deletion_approval(
        tenant_id='tenant-one',
        current='archived',
        target='deleting',
        owner='owner-one',
        revision=3,
        expires_at=NOW + timedelta(hours=1),
        nonce='delete-long-00001',
        key=APPROVAL_KEY,
    )
    with pytest.raises(TenantLifecycleError, match='approval_invalid'):
        transition_tenant(
            tenant_id='tenant-one',
            current='archived',
            target='deleting',
            deletion_approval=long_lived,
            now=NOW,
            approval_key=APPROVAL_KEY,
            expected_revision=3,
            consume_nonce=lambda *_: True,
        )


def test_quota_reservation_is_atomic_replay_safe_and_tenant_bound():
    state = quota_state(tenant_id='tenant-one', limits=limits())
    reserved = reserve_quota(
        state, tenant_id='tenant-one', quota='storage', amount=6, reservation_id='upload-0001'
    )
    assert (
        reserve_quota(
            reserved,
            tenant_id='tenant-one',
            quota='storage',
            amount=6,
            reservation_id='upload-0001',
        )
        == reserved
    )
    with pytest.raises(TenantLifecycleError, match='conflict'):
        reserve_quota(
            reserved,
            tenant_id='tenant-one',
            quota='storage',
            amount=5,
            reservation_id='upload-0001',
        )
    with pytest.raises(TenantLifecycleError, match='exhausted'):
        reserve_quota(
            reserved,
            tenant_id='tenant-one',
            quota='storage',
            amount=5,
            reservation_id='upload-0002',
        )
    with pytest.raises(TenantLifecycleError, match='tenant_mismatch'):
        reserve_quota(
            reserved,
            tenant_id='tenant-two',
            quota='storage',
            amount=1,
            reservation_id='upload-0002',
        )


def test_quota_commit_release_and_reconciliation_are_explicit():
    state = quota_state(tenant_id='tenant-one', limits=limits())
    first = reserve_quota(
        state, tenant_id='tenant-one', quota='jobs', amount=2, reservation_id='jobs-run-0001'
    )
    committed = settle_quota(first, reservation_id='jobs-run-0001', commit=True)
    assert committed['used']['jobs'] == 2 and committed['reserved']['jobs'] == 0
    second = reserve_quota(
        committed, tenant_id='tenant-one', quota='jobs', amount=1, reservation_id='jobs-run-0002'
    )
    released = settle_quota(second, reservation_id='jobs-run-0002', commit=False)
    assert released['used']['jobs'] == 2 and released['reserved']['jobs'] == 0
    result = reconcile_quota(released, measured={**limits(0), 'jobs': 3})
    assert result['drift']['jobs'] == 1
    assert result['crossTenantComparison'] is False


def test_tenant_transfer_export_and_configuration_are_recent_auth_bound():
    transferred = tenant_operation(
        tenant_id='tenant-one',
        operation='transfer_prepare',
        owner='owner-one',
        target_owner='00000000-0000-4000-8000-000000000222',
        recent_auth=True,
    )
    assert transferred['dataPreserved'] and not transferred['destructive']
    assert (
        tenant_operation(
            tenant_id='tenant-one', operation='export', owner='owner-one', recent_auth=True
        )['operation']
        == 'export'
    )
    with pytest.raises(TenantLifecycleError, match='recent_auth'):
        tenant_operation(
            tenant_id='tenant-one', operation='configure', owner='owner-one', recent_auth=False
        )


def test_durable_transition_defers_approval_consumption_to_atomic_repository():
    approval = create_deletion_approval(
        tenant_id='tenant-one',
        current='archived',
        target='deleting',
        owner='owner-one',
        revision=7,
        expires_at=NOW + timedelta(minutes=10),
        nonce='delete-atomic-0001',
        key=APPROVAL_KEY,
    )
    operation_id = UUID('00000000-0000-4000-8000-000000000106')
    with (
        patch('api.repositories.tenant_lifecycle.get_operation_event', return_value=None),
        patch('api.repositories.tenant_lifecycle.get_state') as get_state,
        patch('api.repositories.tenant_lifecycle.apply_transition') as apply_transition,
    ):
        get_state.return_value = {'state': 'archived'}
        apply_transition.return_value = {'state': 'deleting', 'revision': 8}
        result = persist_transition(
            tenant_id='tenant-one',
            target='deleting',
            owner='owner-one',
            expected_revision=7,
            operation_id=operation_id,
            deletion_approval=approval,
            now=NOW,
            approval_key=APPROVAL_KEY,
        )
    assert result['state'] == 'deleting'
    atomic_approval = apply_transition.call_args.kwargs['approval']
    assert atomic_approval['nonce'] == 'delete-atomic-0001'
    assert atomic_approval['digest'] == approval['signature']


def test_production_serving_is_revoked_by_durable_lifecycle_state(monkeypatch):
    monkeypatch.setattr('api.settings.settings.ENV', 'production')
    monkeypatch.setattr(
        'api.repositories.tenant_lifecycle.get_state',
        lambda **_kwargs: {'state': 'suspended'},
    )
    denied = TestClient(app).get('/api/health', headers={'X-Tenant-Id': 'tenant-one'})
    assert denied.status_code == 423
    assert denied.json() == {'detail': 'tenant_not_serving'}

    monkeypatch.setattr(
        'api.repositories.tenant_lifecycle.get_state', lambda **_kwargs: {'state': 'active'}
    )
    admitted = TestClient(app).get('/api/health', headers={'X-Tenant-Id': 'tenant-one'})
    assert admitted.status_code != 423
    assert admitted.json().get('detail') != 'tenant_not_serving'


def test_durable_provision_and_operations_delegate_validated_revisioned_state():
    operation_id = UUID('00000000-0000-4000-8000-000000000107')
    with patch('api.repositories.tenant_lifecycle.provision') as provision:
        provision.return_value = {'state': 'provisioning', 'revision': 1}
        result = persist_provision(
            tenant_id='tenant-one',
            owner='owner-one',
            operation_id=operation_id,
            configuration={'locale': 'en'},
        )
    assert result['revision'] == 1
    assert provision.call_args.kwargs['configuration'] == {'locale': 'en'}

    with (
        patch('api.repositories.tenant_lifecycle.apply_operation') as apply_operation,
        patch('api.repositories.identity_admin.membership', return_value={'role': 'admin'}),
    ):
        apply_operation.return_value = {'state': 'active', 'revision': 4}
        result = persist_operation(
            tenant_id='tenant-one',
            operation='transfer_prepare',
            owner='owner-one',
            target_owner='00000000-0000-4000-8000-000000000222',
            recent_auth=True,
            expected_revision=3,
            operation_id=operation_id,
        )
    assert result['revision'] == 4
    assert (
        apply_operation.call_args.kwargs['target_owner_ref']
        == '00000000-0000-4000-8000-000000000222'
    )


def test_deletion_approval_key_file_is_absolute_owner_only_and_exact_length(tmp_path):
    key_file = tmp_path / 'tenant-delete-key'
    key_file.write_text(base64.urlsafe_b64encode(APPROVAL_KEY).decode(), encoding='ascii')
    key_file.chmod(0o600)
    assert read_approval_key_file(str(key_file)) == APPROVAL_KEY
    key_file.chmod(0o640)
    with pytest.raises(TenantLifecycleError, match='approval_key_invalid'):
        read_approval_key_file(str(key_file))


def test_quota_report_is_tenant_private_and_actionable():
    report = quota_report(quota_state(tenant_id='tenant-one', limits=limits(2)), forecast=limits(3))
    assert report['quotas']['users']['denialReason'] == 'quota-exhausted'
    assert report['quotas']['users']['remediation']
    assert report['crossTenantComparison'] is False


def test_recovery_sessions_policy_and_settings_fail_closed():
    recovery = identity_recovery(
        user_id='user-one', proof_verified=True, method='passkey', existing_factors=1
    )
    assert recovery['rotateSessions'] and not recovery['removeExistingFactors']
    with pytest.raises(TenantLifecycleError, match='downgrade'):
        identity_recovery(
            user_id='user-one', proof_verified=True, method='recovery-code', existing_factors=0
        )
    sessions = [
        {'userId': 'user-one', 'sessionId': 's1', 'state': 'active'},
        {'userId': 'user-two', 'sessionId': 's2', 'state': 'active'},
    ]
    visible = session_action(sessions, user_id='user-one', session_id='s1', action='revoke')
    assert visible == [
        {
            'userId': 'user-one',
            'sessionId': 's1',
            'state': 'revoked',
            'tokenRotationRequired': True,
        }
    ]
    grants = {'editor': ['content.edit']}
    for surface in (
        'django',
        'fastapi',
        'react',
        'worker',
        'export',
        'search',
        'media',
        'administration',
        'operations',
    ):
        assert authorize(role='editor', action='content.edit', surface=surface, grants=grants)
        assert not authorize(role='member', action='content.edit', surface=surface, grants=grants)
    changed = settings_change(
        scope='tenant',
        key='security.mfa',
        expected_revision=2,
        current_revision=2,
        recent_auth=True,
    )
    assert changed['historyRequired'] and changed['unsavedChangeGuard']
    with pytest.raises(TenantLifecycleError, match='revision_conflict'):
        settings_change(
            scope='account',
            key='locale.user',
            expected_revision=1,
            current_revision=2,
            recent_auth=True,
        )


def test_production_request_middleware_denies_nonactive_serving_but_keeps_recovery_route(
    monkeypatch,
):
    monkeypatch.setattr('api.settings.settings.ENV', 'production')
    monkeypatch.setattr(
        'api.repositories.tenant_lifecycle.get_state',
        lambda **_kwargs: {'state': 'suspended'},
    )
    client = TestClient(app)
    denied = client.get('/api/tenants/alpha/echo', headers={'X-Tenant-Id': 'alpha'})
    assert denied.status_code == 423
    assert denied.json() == {'detail': 'tenant_not_serving'}
    recovery = client.get('/api/tenants/alpha/lifecycle', headers={'X-Tenant-Id': 'alpha'})
    assert recovery.status_code != 423
