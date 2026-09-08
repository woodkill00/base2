"""Private, tenant-bound native operations API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from api.middleware.tenant import require_tenant
from api.repositories import operations as repository
from api.repositories.identity_admin import require_permission
from api.security.identity import require_recent_reauthentication
from api.security.request_auth import require_authenticated_principal

router = APIRouter(prefix='/operations/v1', tags=['operations'])


def _scope(request: Request, permission: str):
    principal = require_authenticated_principal(request)
    tenant_id = require_tenant(request)
    try:
        membership = require_permission(
            user_id=principal.user_id,
            tenant_id=tenant_id,
            permission=permission,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='operations_not_found') from exc
    return principal, tenant_id, membership


@router.get('/summary')
def get_summary(request: Request):
    _principal, tenant_id, _membership = _scope(request, 'operations.read')
    return {'schemaVersion': 1, **repository.summary(tenant_id=tenant_id)}


@router.get('/incidents')
def get_incidents(request: Request, limit: int = Query(default=50, ge=1, le=100)):
    _principal, tenant_id, _membership = _scope(request, 'operations.read')
    return {
        'schemaVersion': 1,
        'incidents': repository.list_incidents(tenant_id=tenant_id, limit=limit),
    }


@router.post('/incidents/{incident_id}/acknowledge')
def acknowledge_incident(request: Request, incident_id: UUID):
    principal, tenant_id, membership = _scope(request, 'operations.manage')
    try:
        if not principal.recently_authenticated:
            raise PermissionError('recent_reauthentication_required')
        require_recent_reauthentication(authenticated_at=principal.authenticated_at)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    changed = repository.acknowledge(
        tenant_id=tenant_id,
        incident_id=incident_id,
        owner_ref=f"{membership['role']}:{principal.user_id}",
    )
    if not changed:
        raise HTTPException(status_code=409, detail='incident_state_conflict')
    return {'status': 'acknowledged', 'incidentId': str(incident_id)}
