from typing import Optional

from fastapi import HTTPException, Request

from api.security.tenant_context import TenantBoundaryError, canonical_tenant_id

TENANT_HEADER = 'X-Tenant-Id'


async def tenant_context_middleware(request: Request, call_next):
    """Extract tenant id from header and attach to request.state.

    This does not enforce tenant semantics by itself; routes can consume
    `request.state.tenant_id` or use `require_tenant()` to enforce presence.
    """
    tenant_id = (request.headers.get(TENANT_HEADER, '') or '').strip()
    if tenant_id:
        try:
            request.state.tenant_id = canonical_tenant_id(tenant_id)
        except TenantBoundaryError:
            # Starlette's function middleware runs outside FastAPI's route
            # exception translation. Preserve the failure on request state so
            # the route dependency returns the normal bounded JSON error.
            request.state.tenant_invalid = True
    return await call_next(request)


def require_tenant(request: Request) -> str:
    """Return the current tenant id from header; raise 400 if missing."""
    if getattr(request.state, 'tenant_invalid', False):
        raise HTTPException(status_code=400, detail='tenant_invalid')
    tid = getattr(request.state, 'tenant_id', None)
    if tid:
        try:
            return canonical_tenant_id(tid)
        except TenantBoundaryError as exc:
            raise HTTPException(status_code=400, detail='tenant_invalid') from exc
    raw = (request.headers.get(TENANT_HEADER, '') or '').strip()
    if not raw:
        raise HTTPException(status_code=400, detail='tenant_required')
    try:
        tenant_id = canonical_tenant_id(raw)
    except TenantBoundaryError as exc:
        raise HTTPException(status_code=400, detail='tenant_invalid') from exc
    request.state.tenant_id = tenant_id
    return tenant_id


def ensure_path_tenant_matches(request: Request, path_tenant: Optional[str]) -> str:
    """Ensure the path tenant matches the header tenant.

    Returns the resolved tenant id; raises 403 on mismatch or 400 on missing.
    """
    header_tenant = require_tenant(request)
    pt = (path_tenant or '').strip()
    if not pt:
        raise HTTPException(status_code=400, detail='tenant_path_required')
    if pt != header_tenant:
        raise HTTPException(status_code=403, detail='cross_tenant_forbidden')
    return header_tenant
