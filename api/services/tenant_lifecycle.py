"""Tenant lifecycle and atomic quota state contracts."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

TENANT = re.compile(r'^[a-z][a-z0-9-]{2,62}$')
STATES = {'provisioning', 'active', 'suspended', 'archived', 'restoring', 'deleting', 'deleted'}
QUOTAS = {'users', 'storage', 'media', 'api', 'jobs', 'email', 'search', 'cost'}
SCOPES = {'account', 'tenant', 'site', 'module', 'operator'}
ROLES = {'anonymous', 'member', 'editor', 'administrator', 'operator'}


class TenantLifecycleError(ValueError):
    pass


def transition_tenant(
    *, tenant_id: str, current: str, target: str, exact_deletion_approval: bool = False
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
    if target in {'deleting', 'deleted'} and not exact_deletion_approval:
        raise TenantLifecycleError('tenant:deletion_approval_required')
    receipt = {
        'tenantId': tenant_id,
        'from': current,
        'to': target,
        'servingAuthority': target in {'active'},
        'allocationAuthority': target in {'provisioning', 'active', 'restoring'},
        'recoverableDataPreserved': target != 'deleted',
    }
    receipt['digest'] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    return receipt


def tenant_operation(
    *,
    tenant_id: str,
    operation: str,
    owner: str,
    recent_auth: bool,
    target_owner: str | None = None,
) -> dict[str, Any]:
    """Create a bounded, auditable non-destructive tenant operation."""
    if operation not in {'configure', 'transfer', 'export'} or not TENANT.fullmatch(
        tenant_id or ''
    ):
        raise TenantLifecycleError('tenant:operation_invalid')
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,127}', owner or '') or not recent_auth:
        raise TenantLifecycleError('tenant:recent_auth_required')
    if operation == 'transfer':
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
