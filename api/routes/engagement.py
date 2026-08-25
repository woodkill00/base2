from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from api.middleware.tenant import require_tenant
from api.routes.site_content import get_site_content_service
from api.security import rate_limit
from api.security.engagement import EngagementPolicyError
from api.security.request_auth import require_authenticated_principal
from api.services.site_content import SiteContentService

router=APIRouter(prefix='/engagement',tags=['engagement'])
Service=Annotated[SiteContentService,Depends(get_site_content_service)]
class CommunityRequest(BaseModel):
    title:str=Field(min_length=3,max_length=160)
    body:str=Field(min_length=10,max_length=10000)

@router.post('/community',status_code=202)
def submit_community(payload:CommunityRequest,request:Request,service:Service):
    principal=require_authenticated_principal(request)
    tenant = require_tenant(request)
    client_ip = request.client.host if request.client else 'unknown'
    _count, over, retry_after = rate_limit.incr_and_check_tenant_detailed(
        tenant, client_ip, 'community_submit'
    )
    if over:
        raise HTTPException(
            status_code=429,
            detail='rate_limited',
            headers={'Retry-After': str(retry_after)},
        )
    try:
        return service.submit_community(
            site_id=tenant,
            author_ref=str(principal.user_id),
            title=payload.title,
            body=payload.body,
        )
    except EngagementPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
