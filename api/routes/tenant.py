import os
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from api.middleware.tenant import ensure_path_tenant_matches
from api.repositories import tenant_lifecycle as tenant_lifecycle_repository
from api.repositories import tenant_quota
from api.repositories.identity_admin import membership, require_permission
from api.security.identity import require_recent_reauthentication
from api.security.request_auth import require_authenticated_principal
from api.security.tenant_limits import incr_and_check_detailed
from api.services import tenant_lifecycle

router = APIRouter(prefix='/tenants', tags=['tenants'])


class QuotaReservationRequest(BaseModel):
    amount: int = Field(ge=1, le=9_223_372_036_854_775_807)
    reservation_id: str = Field(alias='reservationId', pattern=r'^[a-z][a-z0-9_.-]{2,95}$')


class QuotaSettlementRequest(BaseModel):
    commit: bool


class TenantProvisionRequest(BaseModel):
    operation_id: UUID = Field(alias='operationId')
    configuration: dict[str, Any] = Field(default_factory=dict)


class TenantTransitionRequest(BaseModel):
    operation_id: UUID = Field(alias='operationId')
    target: Literal['active', 'suspended', 'archived', 'restoring', 'deleting', 'deleted']
    expected_revision: int = Field(alias='expectedRevision', ge=1)
    approval: dict[str, Any] | None = None


class TenantOperationRequest(BaseModel):
    operation_id: UUID = Field(alias='operationId')
    operation: Literal['configure', 'transfer_prepare', 'transfer_accept', 'export']
    expected_revision: int = Field(alias='expectedRevision', ge=1)
    target_owner: str | None = Field(default=None, alias='targetOwner', max_length=127)
    configuration: dict[str, Any] | None = None


def _quota_scope(request: Request, tenant_id: str, permission: str, *, recent: bool = False):
    tid = ensure_path_tenant_matches(request, tenant_id)
    principal = require_authenticated_principal(request)
    try:
        require_permission(user_id=principal.user_id, tenant_id=tid, permission=permission)
        if recent:
            if not principal.recently_authenticated:
                raise PermissionError('recent_reauthentication_required')
            require_recent_reauthentication(authenticated_at=principal.authenticated_at)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return tid


def _lifecycle_scope(request: Request, tenant_id: str, *, recent: bool = False):
    tid = ensure_path_tenant_matches(request, tenant_id)
    principal = require_authenticated_principal(request)
    try:
        require_permission(user_id=principal.user_id, tenant_id=tid, permission='operations.manage')
        if recent:
            if not principal.recently_authenticated:
                raise PermissionError('recent_reauthentication_required')
            require_recent_reauthentication(authenticated_at=principal.authenticated_at)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return principal, tid


@router.get('/{tenant_id}/echo')
async def tenant_echo(tenant_id: str, request: Request):
    # Enforce header/path match
    tid = ensure_path_tenant_matches(request, tenant_id)
    # Per-tenant rate limit on echo (test scope)
    count, over, retry_after = incr_and_check_detailed(tid, scope='tenant_echo')
    if over:
        # Align with rate-limit error envelope
        raise HTTPException(
            status_code=429, detail='rate_limited', headers={'Retry-After': str(retry_after)}
        )
    return {'ok': True, 'tenant_id': tid, 'count': count}


@router.get('/{tenant_id}/lifecycle')
def get_lifecycle(tenant_id: str, request: Request):
    _principal, tid = _lifecycle_scope(request, tenant_id)
    try:
        return {'schemaVersion': 1, **tenant_lifecycle_repository.get_state(tenant_id=tid)}
    except tenant_lifecycle_repository.TenantLifecycleRepositoryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/{tenant_id}/lifecycle/provision', status_code=201)
def provision_lifecycle(tenant_id: str, body: TenantProvisionRequest, request: Request):
    principal, tid = _lifecycle_scope(request, tenant_id, recent=True)
    try:
        return tenant_lifecycle.persist_provision(
            tenant_id=tid,
            owner=str(principal.user_id),
            operation_id=body.operation_id,
            configuration=body.configuration,
        )
    except tenant_lifecycle.TenantLifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{tenant_id}/lifecycle/transition')
def transition_lifecycle(tenant_id: str, body: TenantTransitionRequest, request: Request):
    principal, tid = _lifecycle_scope(request, tenant_id, recent=True)
    key = None
    if body.target in {'deleting', 'deleted'}:
        try:
            key = tenant_lifecycle.read_approval_key_file(
                os.environ.get('TENANT_DELETION_APPROVAL_KEY_FILE', '')
            )
        except tenant_lifecycle.TenantLifecycleError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        return tenant_lifecycle.persist_transition(
            tenant_id=tid,
            target=body.target,
            owner=str(principal.user_id),
            expected_revision=body.expected_revision,
            operation_id=body.operation_id,
            deletion_approval=body.approval,
            now=datetime.now(UTC),
            approval_key=key,
        )
    except tenant_lifecycle.TenantLifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{tenant_id}/lifecycle/operations')
def run_lifecycle_operation(tenant_id: str, body: TenantOperationRequest, request: Request):
    if body.operation == 'transfer_accept':
        tid = ensure_path_tenant_matches(request, tenant_id)
        principal = require_authenticated_principal(request)
        try:
            if membership(user_id=principal.user_id, tenant_id=tid) is None:
                raise PermissionError('not_found')
            if not principal.recently_authenticated:
                raise PermissionError('recent_reauthentication_required')
            require_recent_reauthentication(authenticated_at=principal.authenticated_at)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    else:
        principal, tid = _lifecycle_scope(request, tenant_id, recent=True)
    try:
        return tenant_lifecycle.persist_operation(
            tenant_id=tid,
            operation=body.operation,
            owner=str(principal.user_id),
            recent_auth=True,
            expected_revision=body.expected_revision,
            operation_id=body.operation_id,
            target_owner=body.target_owner,
            configuration=body.configuration,
        )
    except tenant_lifecycle.TenantLifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get('/{tenant_id}/quotas')
def get_quotas(tenant_id: str, request: Request):
    tid = _quota_scope(request, tenant_id, 'operations.read')
    return {'schemaVersion': 1, 'quotas': tenant_quota.list_quotas(tenant_id=tid)}


@router.post('/{tenant_id}/quotas/{quota_key}/reservations')
def reserve_quota(tenant_id: str, quota_key: str, body: QuotaReservationRequest, request: Request):
    tid = _quota_scope(request, tenant_id, 'operations.manage', recent=True)
    try:
        return tenant_quota.reserve(
            tenant_id=tid,
            quota_key=quota_key,
            amount=body.amount,
            reservation_id=body.reservation_id,
        )
    except tenant_quota.QuotaRepositoryError as exc:
        status = 409 if str(exc) in {'quota:exhausted', 'quota:reservation_conflict'} else 404
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post('/{tenant_id}/quotas/reservations/{reservation_id}/settle')
def settle_quota(
    tenant_id: str, reservation_id: str, body: QuotaSettlementRequest, request: Request
):
    tid = _quota_scope(request, tenant_id, 'operations.manage', recent=True)
    try:
        return tenant_quota.settle(tenant_id=tid, reservation_id=reservation_id, commit=body.commit)
    except tenant_quota.QuotaRepositoryError as exc:
        status = 409 if str(exc) == 'quota:settlement_conflict' else 404
        raise HTTPException(status_code=status, detail=str(exc)) from exc
