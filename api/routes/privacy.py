from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, ValidationError

from api.auth.repo import insert_audit_event
from api.middleware.tenant import require_tenant
from api.repositories import data_rights as repository
from api.repositories.identity_admin import require_permission
from api.security.identity import require_recent_reauthentication
from api.security.request_auth import require_authenticated_principal
from api.security.secret_box import SecretBox, SecretBoxError
from api.services.data_rights import receipt_digest, validate_correction, verify_receipt
from api.settings import settings

router = APIRouter(prefix='/privacy', tags=['privacy'])


class CorrectionRequest(BaseModel):
    fields: dict[str, str]


class DeletionRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=20)


def _recent_principal(request: Request):
    principal = require_authenticated_principal(request)
    if not principal.recently_authenticated:
        raise HTTPException(status_code=401, detail='recent_reauthentication_required')
    try:
        require_recent_reauthentication(authenticated_at=principal.authenticated_at)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail='recent_reauthentication_required') from exc
    return principal


def _box() -> SecretBox:
    try:
        return SecretBox(str(settings.IDENTITY_ENCRYPTION_KEY or '').strip())
    except SecretBoxError as exc:
        raise HTTPException(status_code=503, detail='privacy_workflow_unavailable') from exc


def _public_operation(operation: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(operation['id']),
        'kind': operation['kind'],
        'status': operation['status'],
        'error_code': operation.get('error_code') or '',
        'created_at': operation['created_at'],
        'completed_at': operation.get('completed_at'),
        'retention_until': operation['retention_until'],
    }


def _dispatch(operation_id: UUID) -> str:
    try:
        from api.tasks import process_data_rights_operation

        process_data_rights_operation.delay(str(operation_id))
        return 'queued'
    except Exception:
        # The durable queued row is replayed by the bounded periodic scanner.
        return 'deferred'


def _enqueue(*, request: Request, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    operation_id, created = repository.create_operation(
        tenant_id=tenant_id,
        user_id=principal.user_id,
        kind=kind,
        request_ciphertext=_box().encrypt(json.dumps(payload, separators=(',', ':'), sort_keys=True)),
    )
    dispatch = _dispatch(operation_id) if created else 'already_active'
    insert_audit_event(
        user_id=principal.user_id,
        action=f'privacy.{kind}_requested',
        ip=request.client.host if request.client else '',
        user_agent=request.headers.get('user-agent', ''),
        metadata={
            'operation_id': str(operation_id), 'tenant_id': tenant_id,
            'created': created, 'dispatch': dispatch,
        },
    )
    return {
        'accepted': True, 'operation_id': str(operation_id), 'kind': kind,
        'status': 'queued', 'dispatch': dispatch, 'idempotent': not created,
    }


@router.post('/export', status_code=status.HTTP_202_ACCEPTED)
async def export_data(request: Request):
    return _enqueue(request=request, kind='export', payload={'schema_version': 1})


@router.post('/correct', status_code=status.HTTP_202_ACCEPTED)
async def correct_data(request: Request):
    _recent_principal(request)
    require_tenant(request)
    try:
        payload = CorrectionRequest.model_validate(await request.json())
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail='request_invalid') from exc
    try:
        fields = validate_correction(payload.fields)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _enqueue(request=request, kind='correction', payload={'fields': fields})


@router.post('/delete', status_code=status.HTTP_202_ACCEPTED)
async def delete_data(request: Request):
    _recent_principal(request)
    require_tenant(request)
    try:
        payload = DeletionRequest.model_validate(await request.json())
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail='request_invalid') from exc
    if payload.confirmation != 'DELETE':
        raise HTTPException(status_code=422, detail='deletion_confirmation_invalid')
    return _enqueue(request=request, kind='deletion', payload={'confirmation': 'DELETE'})


@router.get('/operations')
async def list_operations(request: Request, limit: int = 50):
    principal = require_authenticated_principal(request)
    tenant_id = require_tenant(request)
    return {
        'operations': [
            _public_operation(item)
            for item in repository.list_owned_operations(
                tenant_id=tenant_id, user_id=principal.user_id, limit=limit
            )
        ]
    }


@router.get('/operations/{operation_id}')
async def get_operation(operation_id: UUID, request: Request):
    principal = require_authenticated_principal(request)
    tenant_id = require_tenant(request)
    operation = repository.owned_operation(
        operation_id=operation_id, tenant_id=tenant_id, user_id=principal.user_id
    )
    if operation is None:
        raise HTTPException(status_code=404, detail='not_found')
    return _public_operation(operation)


@router.get('/operations/{operation_id}/download')
async def download_export(operation_id: UUID, request: Request):
    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    operation = repository.owned_operation(
        operation_id=operation_id, tenant_id=tenant_id, user_id=principal.user_id
    )
    if operation is None or operation['kind'] != 'export':
        raise HTTPException(status_code=404, detail='not_found')
    if operation['status'] != 'completed' or not operation['result_ciphertext']:
        raise HTTPException(status_code=409, detail='export_not_ready')
    try:
        payload = json.loads(_box().decrypt(operation['result_ciphertext']))
    except (SecretBoxError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=409, detail='export_integrity_failed') from exc
    if not verify_receipt(
        operation_id=str(operation_id), tenant_id=tenant_id,
        user_id=str(principal.user_id), payload=payload, key=settings.TOKEN_PEPPER,
        digest=operation['receipt_digest'],
    ):
        raise HTTPException(status_code=409, detail='export_integrity_failed')
    digest = receipt_digest(
        operation_id=str(operation_id), tenant_id=tenant_id,
        user_id=str(principal.user_id), payload=payload, key=settings.TOKEN_PEPPER,
    )
    return Response(
        content=json.dumps(payload, ensure_ascii=False, separators=(',', ':'), sort_keys=True),
        media_type='application/json',
        headers={
            'Cache-Control': 'no-store',
            'Content-Disposition': f'attachment; filename="data-export-{operation_id}.json"',
            'X-Export-Receipt-SHA256': digest,
        },
    )


@router.get('/admin/operations')
async def admin_operations(request: Request, limit: int = 100):
    principal = require_authenticated_principal(request)
    tenant_id = require_tenant(request)
    try:
        require_permission(
            user_id=principal.user_id, tenant_id=tenant_id, permission='audit.read'
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='not_found') from exc
    return {
        'operations': [
            {**_public_operation(item), 'user_id': str(item['user_id'])}
            for item in repository.list_tenant_operations(tenant_id=tenant_id, limit=limit)
        ]
    }
