from fastapi import APIRouter, Request
from api.middleware.tenant import require_tenant
from api.security.request_auth import require_authenticated_user

router = APIRouter(prefix='/privacy', tags=['privacy'])


@router.post('/export')
async def export_data(request: Request):
    require_authenticated_user(request)
    tenant_id = require_tenant(request)
    # In a full implementation, queue an export task and return a tracking id.
    # Here we return a simple accepted response with minimal metadata.
    return {'accepted': True, 'operation': 'export', 'tenant_id': tenant_id}


@router.post('/correct')
async def correct_data(request: Request):
    require_authenticated_user(request)
    tenant_id = require_tenant(request)
    return {'accepted': True, 'operation': 'correct', 'tenant_id': tenant_id}


@router.post('/delete')
async def delete_data(request: Request):
    require_authenticated_user(request)
    tenant_id = require_tenant(request)
    # In a full implementation, enqueue deletion per privacy policy and audit it.
    return {'accepted': True, 'operation': 'delete', 'tenant_id': tenant_id}
