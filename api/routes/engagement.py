from typing import Annotated
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from api.middleware.tenant import require_tenant
from api.routes.site_content import get_site_content_service
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
    return service.submit_community(site_id=require_tenant(request),author_ref=str(principal.user_id),title=payload.title,body=payload.body)
