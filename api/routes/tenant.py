from fastapi import APIRouter, Request, HTTPException

from api.middleware.tenant import ensure_path_tenant_matches
from api.security.tenant_limits import incr_and_check_detailed

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/{tenant_id}/echo")
async def tenant_echo(tenant_id: str, request: Request):
    # Enforce header/path match
    tid = ensure_path_tenant_matches(request, tenant_id)
    # Per-tenant rate limit on echo (test scope)
    count, over, retry_after = incr_and_check_detailed(tid, scope="tenant_echo")
    if over:
        # Align with rate-limit error envelope
        raise HTTPException(status_code=429, detail="rate_limited", headers={"Retry-After": str(retry_after)})
    return {"ok": True, "tenant_id": tid, "count": count}
