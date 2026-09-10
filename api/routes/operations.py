"""Private, tenant-bound native operations API."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from api.middleware.tenant import require_tenant
from api.repositories import operations as repository
from api.repositories.runtime_governance import RuntimeRepositoryError, dead_letter_action
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


@router.get('/overview')
def get_overview(request: Request):
    _principal, tenant_id, _membership = _scope(request, 'operations.read')
    return {'schemaVersion': 1, **repository.overview(tenant_id=tenant_id)}


@router.get('/incidents/{incident_id}')
def get_incident(request: Request, incident_id: UUID):
    _principal, tenant_id, _membership = _scope(request, 'operations.read')
    incident = repository.incident_detail(tenant_id=tenant_id, incident_id=incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail='incident_not_found')
    return {'schemaVersion': 1, 'incident': incident}


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


@router.post('/runtime/dead-letters/{job_id}/{action}')
def act_on_dead_letter(request: Request, job_id: UUID, action: str):
    """Apply one fixed, recent-authenticated dead-letter transition."""
    principal, tenant_id, _membership = _scope(request, 'operations.manage')
    try:
        if not principal.recently_authenticated:
            raise PermissionError('recent_reauthentication_required')
        require_recent_reauthentication(authenticated_at=principal.authenticated_at)
        state = dead_letter_action(
            tenant_id=tenant_id,
            job_id=job_id,
            action=action,
            now=datetime.now(UTC),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeRepositoryError as exc:
        status = 409 if str(exc) == 'job:dead_letter_state_invalid' else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return {'status': state, 'jobId': str(job_id), 'action': action}
