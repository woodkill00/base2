"""Tenant lifecycle and atomic quota state contracts."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import base64
import binascii
import stat
from pathlib import Path
from datetime import UTC, datetime, timedelta
from collections.abc import Callable
from typing import Any
from uuid import UUID

TENANT = re.compile(r'^[a-z][a-z0-9-]{2,62}$')
STATES = {'provisioning', 'active', 'suspended', 'archived', 'restoring', 'deleting', 'deleted'}
QUOTAS = {'users', 'storage', 'media', 'api', 'jobs', 'email', 'search', 'cost'}
SCOPES = {'account', 'tenant', 'site', 'module', 'operator'}
ROLES = {'anonymous', 'member', 'editor', 'administrator', 'operator'}


class TenantLifecycleError(ValueError):
    pass


def read_approval_key_file(path: str) -> bytes:
    """Read one owner-only base64url key without accepting symlinks or ambient values."""
    candidate = Path(path)
    if not candidate.is_absolute() or candidate.is_symlink():
        raise TenantLifecycleError('tenant:approval_key_invalid')
    try:
        metadata = candidate.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            raise TenantLifecycleError('tenant:approval_key_invalid')
        encoded = candidate.read_text(encoding='ascii').strip()
        if not encoded or len(encoded) > 256:
            raise TenantLifecycleError('tenant:approval_key_invalid')
        key = base64.b64decode(encoded + '=' * (-len(encoded) % 4), altchars=b'-_', validate=True)
    except (OSError, UnicodeError, ValueError, binascii.Error) as exc:
        raise TenantLifecycleError('tenant:approval_key_invalid') from exc
    if len(key) != 32:
        raise TenantLifecycleError('tenant:approval_key_invalid')
    return key


def transition_tenant(
    *,
    tenant_id: str,
    current: str,
    target: str,
    deletion_approval: dict[str, Any] | None = None,
    now: datetime | None = None,
    approval_key: bytes | None = None,
    expected_revision: int | None = None,
    consume_nonce: Callable[[str, str, str, datetime], bool] | None = None,
) -> dict[str, Any]:
    allowed = {
        'provisioning': {'active'},
        'active': {'suspended', 'archived'},
        'suspended': {'active', 'archived'},
        'archived': {'restoring', 'deleting'},
        'restoring': {'active'},
        'deleting': {'deleted'},
        'deleted': set(),
    }
    if (
        not TENANT.fullmatch(tenant_id or '')
        or current not in STATES
        or target not in allowed[current]
    ):
        raise TenantLifecycleError('tenant:transition_invalid')
    if target in {'deleting', 'deleted'}:
        _verify_deletion_approval(
            deletion_approval,
            tenant_id=tenant_id,
            current=current,
            target=target,
            now=now,
            key=approval_key,
            expected_revision=expected_revision,
            consume_nonce=consume_nonce,
        )
    receipt = {
        'tenantId': tenant_id,
        'from': current,
        'to': target,
        'servingAuthority': target in {'active'},
        'allocationAuthority': target in {'provisioning', 'active', 'restoring'},
        'recoverableDataPreserved': True if target != 'deleted' else None,
        # The state revokes authority; it never fabricates proof that every
        # data plane has completed erasure. A separate reconciler owns that proof.
        'dataDeletionVerified': False,
        'deletionVerificationRequired': target == 'deleted',
    }
    receipt['digest'] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    return receipt


def create_deletion_approval(
    *,
    tenant_id: str,
    current: str,
    target: str,
    owner: str,
    revision: int,
    expires_at: datetime,
    nonce: str,
    key: bytes,
) -> dict[str, Any]:
    if (
        not TENANT.fullmatch(tenant_id or '')
        or (current, target) not in {('archived', 'deleting'), ('deleting', 'deleted')}
        or not re.fullmatch(r'[A-Za-z0-9._-]{3,127}', owner or '')
        or revision < 1
        or expires_at.tzinfo is None
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{15,127}', nonce or '')
        or len(key) < 32
    ):
        raise TenantLifecycleError('tenant:deletion_approval_invalid')
    value = {
        'tenantId': tenant_id,
        'from': current,
        'to': target,
        'owner': owner,
        'revision': revision,
        'expiresAt': expires_at.astimezone(UTC).isoformat(),
        'nonce': nonce,
    }
    value['signature'] = hmac.new(
        key, json.dumps(value, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256
    ).hexdigest()
    return value


def _verify_deletion_approval(
    value: dict[str, Any] | None,
    *,
    tenant_id: str,
    current: str,
    target: str,
    now: datetime | None,
    key: bytes | None,
    expected_revision: int | None,
    consume_nonce: Callable[[str, str, str, datetime], bool] | None,
) -> str:
    required = {'tenantId', 'from', 'to', 'owner', 'revision', 'expiresAt', 'nonce', 'signature'}
    if (
        not isinstance(value, dict)
        or set(value) != required
        or now is None
        or now.tzinfo is None
        or type(expected_revision) is not int
        or expected_revision < 1
        or not callable(consume_nonce)
    ):
        raise TenantLifecycleError('tenant:deletion_approval_required')
    if key is None or len(key) < 32:
        raise TenantLifecycleError('tenant:deletion_approval_invalid')
    unsigned = {name: value[name] for name in value if name != 'signature'}
    expected = hmac.new(
        key, json.dumps(unsigned, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256
    ).hexdigest()
    try:
        expiry = datetime.fromisoformat(str(value['expiresAt']))
    except ValueError as exc:
        raise TenantLifecycleError('tenant:deletion_approval_invalid') from exc
    if (
        not hmac.compare_digest(str(value['signature']), expected)
        or value['tenantId'] != tenant_id
        or value['from'] != current
        or value['to'] != target
        or value['revision'] != expected_revision
        or expiry <= now
        or expiry > now + timedelta(minutes=15)
    ):
        raise TenantLifecycleError('tenant:deletion_approval_invalid')
    nonce = str(value['nonce'])
    if not consume_nonce(tenant_id, nonce, expected, expiry):
        raise TenantLifecycleError('tenant:deletion_approval_invalid')
    return nonce


def validate_deletion_approval(
    value: dict[str, Any] | None,
    *,
    tenant_id: str,
    current: str,
    target: str,
    now: datetime,
    key: bytes,
    expected_revision: int,
) -> dict[str, Any]:
    """Validate without consuming; persistence must consume in the state transaction."""
    nonce = _verify_deletion_approval(
        value,
        tenant_id=tenant_id,
        current=current,
        target=target,
        now=now,
        key=key,
        expected_revision=expected_revision,
        consume_nonce=lambda *_args: True,
    )
    assert value is not None
    unsigned = {name: value[name] for name in value if name != 'signature'}
    return {
        'nonce': nonce,
        'digest': hmac.new(
            key,
            json.dumps(unsigned, sort_keys=True, separators=(',', ':')).encode(),
            hashlib.sha256,
        ).hexdigest(),
        'expiresAt': datetime.fromisoformat(str(value['expiresAt'])),
    }


def persist_transition(
    *,
    tenant_id: str,
    target: str,
    owner: str,
    expected_revision: int,
    operation_id: UUID,
    deletion_approval: dict[str, Any] | None = None,
    now: datetime | None = None,
    approval_key: bytes | None = None,
) -> dict[str, Any]:
    """Validate and atomically persist a lifecycle transition and any approval use."""
    from api.repositories import tenant_lifecycle as repository

    if not re.fullmatch(r'[A-Za-z0-9._-]{3,127}', owner or ''):
        raise TenantLifecycleError('tenant:owner_invalid')
    replay = repository.get_operation_event(tenant_id=tenant_id, operation_id=operation_id)
    if replay:
        if (
            replay['operation'] != 'transition'
            or replay['to'] != target
            or replay['actor'] != owner
            or replay['revision'] != expected_revision + 1
        ):
            raise TenantLifecycleError('tenant:operation_conflict')
        state = repository.get_state(tenant_id=tenant_id)
        return {**state, 'idempotent': True}
    state = repository.get_state(tenant_id=tenant_id)
    current = str(state['state'])
    if target == 'deleted':
        # Only a dedicated reconciler with per-surface integrity receipts may
        # commit the terminal state. An owner transition alone is insufficient.
        raise TenantLifecycleError('tenant:deletion_reconciliation_required')
    # Exercise the same closed transition graph without consuming the approval.
    transition_tenant(
        tenant_id=tenant_id,
        current=current,
        target=target,
        deletion_approval=deletion_approval,
        now=now,
        approval_key=approval_key,
        expected_revision=expected_revision,
        consume_nonce=(lambda *_args: True) if target in {'deleting', 'deleted'} else None,
    )
    approval = None
    if target in {'deleting', 'deleted'}:
        if now is None or approval_key is None:
            raise TenantLifecycleError('tenant:deletion_approval_required')
        approval = validate_deletion_approval(
            deletion_approval,
            tenant_id=tenant_id,
            current=current,
            target=target,
            now=now,
            key=approval_key,
            expected_revision=expected_revision,
        )
    try:
        return repository.apply_transition(
            tenant_id=tenant_id,
            current=current,
            target=target,
            owner_ref=owner,
            expected_revision=expected_revision,
            operation_id=operation_id,
            approval=approval,
        )
    except repository.TenantLifecycleRepositoryError as exc:
        raise TenantLifecycleError(str(exc)) from exc


def persist_provision(
    *,
    tenant_id: str,
    owner: str,
    operation_id: UUID,
    configuration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the initial durable provisioning state exactly once."""
    from api.repositories import tenant_lifecycle as repository

    if (
        not TENANT.fullmatch(tenant_id or '')
        or not re.fullmatch(r'[A-Za-z0-9._-]{3,127}', owner or '')
        or not isinstance(configuration or {}, dict)
    ):
        raise TenantLifecycleError('tenant:provision_invalid')
    encoded = json.dumps(configuration or {}, sort_keys=True, separators=(',', ':'))
    if len(encoded.encode()) > 16_384 or len(configuration or {}) > 64:
        raise TenantLifecycleError('tenant:configuration_invalid')
    try:
        return repository.provision(
            tenant_id=tenant_id,
            owner_ref=owner,
            operation_id=operation_id,
            configuration=configuration or {},
        )
    except repository.TenantLifecycleRepositoryError as exc:
        raise TenantLifecycleError(str(exc)) from exc


def persist_operation(
    *,
    tenant_id: str,
    operation: str,
    owner: str,
    recent_auth: bool,
    expected_revision: int,
    operation_id: UUID,
    target_owner: str | None = None,
    configuration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and persist configure, transfer, or export as a revisioned event."""
    from api.repositories import tenant_lifecycle as repository

    tenant_operation(
        tenant_id=tenant_id,
        operation=operation,
        owner=owner,
        recent_auth=recent_auth,
        target_owner=target_owner,
    )
    if operation == 'configure':
        if not isinstance(configuration, dict) or len(configuration) > 64:
            raise TenantLifecycleError('tenant:configuration_invalid')
        encoded = json.dumps(configuration, sort_keys=True, separators=(',', ':'))
        if len(encoded.encode()) > 16_384:
            raise TenantLifecycleError('tenant:configuration_invalid')
    elif configuration is not None:
        raise TenantLifecycleError('tenant:configuration_forbidden')
    if operation == 'transfer_prepare':
        try:
            from api.repositories.identity_admin import membership

            target_id = UUID(str(target_owner))
            target_membership = membership(user_id=target_id, tenant_id=tenant_id)
            if target_membership is None:
                raise TenantLifecycleError('tenant:target_owner_not_member')
            if target_membership['role'] not in {'owner', 'admin'}:
                raise TenantLifecycleError('tenant:target_owner_not_administrator')
        except (ValueError, TypeError) as exc:
            raise TenantLifecycleError('tenant:target_owner_invalid') from exc
    try:
        return repository.apply_operation(
            tenant_id=tenant_id,
            operation=operation,
            owner_ref=owner,
            target_owner_ref=target_owner or '',
            configuration=configuration,
            expected_revision=expected_revision,
            operation_id=operation_id,
        )
    except repository.TenantLifecycleRepositoryError as exc:
        raise TenantLifecycleError(str(exc)) from exc


def tenant_operation(
    *,
    tenant_id: str,
    operation: str,
    owner: str,
    recent_auth: bool,
    target_owner: str | None = None,
) -> dict[str, Any]:
    """Create a bounded, auditable non-destructive tenant operation."""
    if operation not in {
        'configure',
        'transfer_prepare',
        'transfer_accept',
        'export',
    } or not TENANT.fullmatch(tenant_id or ''):
        raise TenantLifecycleError('tenant:operation_invalid')
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,127}', owner or '') or not recent_auth:
        raise TenantLifecycleError('tenant:recent_auth_required')
    if operation == 'transfer_prepare':
        if (
            not target_owner
            or target_owner == owner
            or not re.fullmatch(r'[A-Za-z0-9._-]{3,127}', target_owner)
        ):
            raise TenantLifecycleError('tenant:target_owner_invalid')
    elif target_owner is not None:
        raise TenantLifecycleError('tenant:target_owner_forbidden')
    receipt = {
        'tenantId': tenant_id,
        'operation': operation,
        'owner': owner,
        'targetOwner': target_owner,
        'destructive': False,
        'dataPreserved': True,
    }
    receipt['digest'] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    return receipt


def quota_state(*, tenant_id: str, limits: dict[str, int]) -> dict[str, Any]:
    if (
        not TENANT.fullmatch(tenant_id or '')
        or set(limits) != QUOTAS
        or any(type(value) is not int or value < 0 for value in limits.values())
    ):
        raise TenantLifecycleError('quota:limits_invalid')
    return {
        'tenantId': tenant_id,
        'limits': dict(limits),
        'used': {name: 0 for name in QUOTAS},
        'reserved': {name: 0 for name in QUOTAS},
        'reservations': {},
        'generation': 1,
    }


def reserve_quota(
    state: dict[str, Any], *, tenant_id: str, quota: str, amount: int, reservation_id: str
) -> dict[str, Any]:
    if state.get('tenantId') != tenant_id:
        raise TenantLifecycleError('quota:tenant_mismatch')
    if (
        quota not in QUOTAS
        or type(amount) is not int
        or amount < 1
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', reservation_id or '')
    ):
        raise TenantLifecycleError('quota:reservation_invalid')
    value = json.loads(json.dumps(state))
    existing = value['reservations'].get(reservation_id)
    candidate = {'quota': quota, 'amount': amount, 'state': 'reserved'}
    if existing:
        if existing != candidate:
            raise TenantLifecycleError('quota:reservation_conflict')
        return value
    if value['used'][quota] + value['reserved'][quota] + amount > value['limits'][quota]:
        raise TenantLifecycleError('quota:exhausted')
    value['reservations'][reservation_id] = candidate
    value['reserved'][quota] += amount
    value['generation'] += 1
    return value


def settle_quota(state: dict[str, Any], *, reservation_id: str, commit: bool) -> dict[str, Any]:
    value = json.loads(json.dumps(state))
    reservation = value['reservations'].get(reservation_id)
    if not reservation or reservation['state'] != 'reserved':
        raise TenantLifecycleError('quota:reservation_missing')
    quota, amount = reservation['quota'], reservation['amount']
    value['reserved'][quota] -= amount
    if commit:
        value['used'][quota] += amount
    reservation['state'] = 'committed' if commit else 'released'
    value['generation'] += 1
    return value


def reconcile_quota(state: dict[str, Any], *, measured: dict[str, int]) -> dict[str, Any]:
    if set(measured) != QUOTAS or any(
        type(value) is not int or value < 0 for value in measured.values()
    ):
        raise TenantLifecycleError('quota:measurement_invalid')
    value = json.loads(json.dumps(state))
    drift = {name: measured[name] - value['used'][name] for name in sorted(QUOTAS)}
    value['used'] = dict(measured)
    value['generation'] += 1
    return {'state': value, 'drift': drift, 'crossTenantComparison': False}


def quota_report(state: dict[str, Any], *, forecast: dict[str, int]) -> dict[str, Any]:
    if set(forecast) != QUOTAS or any(
        type(value) is not int or value < 0 for value in forecast.values()
    ):
        raise TenantLifecycleError('quota:forecast_invalid')
    rows = {}
    for name in sorted(QUOTAS):
        limit = state['limits'][name]
        committed = state['used'][name]
        reserved = state['reserved'][name]
        projected = committed + reserved + forecast[name]
        rows[name] = {
            'limit': limit,
            'used': committed,
            'reserved': reserved,
            'forecast': forecast[name],
            'remaining': max(0, limit - committed - reserved),
            'denialReason': 'quota-exhausted' if projected > limit else None,
            'alert': projected >= limit,
            'remediation': 'release-reservation-or-request-owner-review'
            if projected > limit
            else None,
        }
    return {'tenantId': state['tenantId'], 'quotas': rows, 'crossTenantComparison': False}


def identity_recovery(
    *, user_id: str, proof_verified: bool, method: str, existing_factors: int
) -> dict[str, Any]:
    if method not in {'recovery-code', 'passkey', 'totp'} or existing_factors < 0:
        raise TenantLifecycleError('identity:recovery_invalid')
    if not proof_verified:
        raise TenantLifecycleError('identity:proof_required')
    if method == 'recovery-code' and existing_factors < 1:
        raise TenantLifecycleError('identity:downgrade_forbidden')
    return {
        'userId': user_id,
        'method': method,
        'rotateSessions': True,
        'rotateRecoveryCodes': method == 'recovery-code',
        'removeExistingFactors': False,
        'securityAlert': True,
    }


def session_action(
    sessions: list[dict[str, Any]], *, user_id: str, session_id: str, action: str
) -> list[dict[str, Any]]:
    if action not in {'list', 'revoke'}:
        raise TenantLifecycleError('session:action_invalid')
    owned = [json.loads(json.dumps(item)) for item in sessions if item.get('userId') == user_id]
    if action == 'list':
        return owned
    found = False
    for item in owned:
        if item.get('sessionId') == session_id:
            item['state'] = 'revoked'
            item['tokenRotationRequired'] = True
            found = True
    if not found:
        raise TenantLifecycleError('session:not_found')
    return owned


def authorize(*, role: str, action: str, surface: str, grants: dict[str, list[str]]) -> bool:
    if role not in ROLES or surface not in {
        'django',
        'fastapi',
        'react',
        'worker',
        'export',
        'search',
        'media',
        'administration',
        'operations',
    }:
        return False
    return action in grants.get(role, [])


def settings_change(
    *, scope: str, key: str, expected_revision: int, current_revision: int, recent_auth: bool
) -> dict[str, Any]:
    if scope not in SCOPES or not CODE_LIKE.fullmatch(key or ''):
        raise TenantLifecycleError('settings:invalid')
    if expected_revision != current_revision:
        raise TenantLifecycleError('settings:revision_conflict')
    sensitive = scope in {'tenant', 'operator'} or key.startswith('security.')
    if sensitive and not recent_auth:
        raise TenantLifecycleError('settings:recent_auth_required')
    return {
        'scope': scope,
        'key': key,
        'revision': current_revision + 1,
        'historyRequired': sensitive,
        'unsavedChangeGuard': True,
        'consequenceCopyRequired': sensitive,
    }


CODE_LIKE = re.compile(r'^[a-z][a-z0-9_.-]{2,95}$')
