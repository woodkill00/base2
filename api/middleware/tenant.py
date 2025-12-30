from typing import Optional
from fastapi import Request, HTTPException

TENANT_HEADER = "X-Tenant-Id"


async def tenant_context_middleware(request: Request, call_next):
    """Extract tenant id from header and attach to request.state.

    This does not enforce tenant semantics by itself; routes can consume
    `request.state.tenant_id` or use `require_tenant()` to enforce presence.
    """
    tenant_id = (request.headers.get(TENANT_HEADER, "") or "").strip()
    if tenant_id:
        request.state.tenant_id = tenant_id
    return await call_next(request)


def require_tenant(request: Request) -> str:
    """Return the current tenant id from header; raise 400 if missing."""
    tid = getattr(request.state, "tenant_id", None)
    if tid:
        return str(tid)
    raw = (request.headers.get(TENANT_HEADER, "") or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="tenant_required")
    request.state.tenant_id = raw
    return raw


def ensure_path_tenant_matches(request: Request, path_tenant: Optional[str]) -> str:
    """Ensure the path tenant matches the header tenant.

    Returns the resolved tenant id; raises 403 on mismatch or 400 on missing.
    """
    header_tenant = require_tenant(request)
    pt = (path_tenant or "").strip()
    if not pt:
        raise HTTPException(status_code=400, detail="tenant_path_required")
    if pt != header_tenant:
        raise HTTPException(status_code=403, detail="cross_tenant_forbidden")
    return header_tenant
