from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from api.middleware.tenant import require_tenant
from api.repositories.scheduling import SchedulingRepository
from api.security.request_auth import require_authenticated_principal

router = APIRouter(prefix='/scheduling', tags=['scheduling'])

class BookingRequest(BaseModel):
    seats: int = Field(ge=1, le=20)

def repository(): return SchedulingRepository()
Repository = Annotated[SchedulingRepository, Depends(repository)]

@router.get('/events')
def list_events(request: Request, store: Repository):
    return {'items': store.list_events(site_id=require_tenant(request))}

@router.post('/events/{event_id}/bookings', status_code=201)
def reserve(event_id: UUID, payload: BookingRequest, request: Request, store: Repository):
    principal = require_authenticated_principal(request)
    try:
        result = store.reserve(site_id=require_tenant(request), event_id=event_id,
                               attendee_ref=str(principal.user_id), seats=payload.seats)
    except ValueError as exc:
        code = str(exc)
        status = 404 if code == 'event_not_found' else 409
        raise HTTPException(status_code=status, detail=code) from exc
    if result['replayed']:
        return {**result, 'statusCode': 200}
    return result
