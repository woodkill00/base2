from __future__ import annotations

import hmac
import re
from datetime import datetime
from typing import Annotated, Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, Field

from api.middleware.tenant import require_tenant
from api.repositories.site_content import PostgresSiteContentRepository
from api.services.site_content import SiteContentService
from api.security import rate_limit
from api.security.public_content import FormPolicyError
from api.settings import settings

router = APIRouter()
_SITE_ID = re.compile(r'^[a-z][a-z0-9-]{2,62}$')


class ContentItem(BaseModel):
    id: UUID
    contentType: str
    slug: str
    title: str
    excerpt: str
    body: str
    metadata: dict[str, Any]
    publishedAt: datetime | None
    updatedAt: datetime


class ContentPage(BaseModel):
    items: list[ContentItem]
    nextCursor: str | None


class MediaItem(BaseModel):
    id: UUID
    name: str
    mediaType: str
    byteSize: int
    sha256: str
    attribution: str
    metadata: dict[str, Any]
    updatedAt: datetime


class SearchItem(BaseModel):
    id: UUID
    title: str
    excerpt: str
    urlPath: str
    indexedAt: datetime


class SearchPage(BaseModel):
    items: list[SearchItem]
    nextCursor: str | None
    freshThrough: datetime


class FormRequest(BaseModel):
    payload: dict[str, Any]
    consent: dict[str, Any] = Field(default_factory=dict)


class FormReceipt(BaseModel):
    id: UUID
    status: str
    replayed: bool
    receivedAt: datetime


def get_site_content_service() -> SiteContentService:
    return SiteContentService(PostgresSiteContentRepository())


SiteContentDependency = Annotated[SiteContentService, Depends(get_site_content_service)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
Slug = Annotated[str, Path(pattern=r'^[a-z0-9][a-z0-9-]{0,159}$')]


def _tenant(request: Request) -> str:
    tenant = require_tenant(request)
    if not _SITE_ID.fullmatch(tenant):
        raise HTTPException(status_code=400, detail='tenant_invalid')
    return tenant


def _map_value_error(exc: ValueError) -> NoReturn:
    if str(exc) == 'invalid_cursor':
        raise HTTPException(status_code=400, detail='invalid_cursor') from exc
    if str(exc) == 'idempotency_conflict':
        raise HTTPException(status_code=409, detail='idempotency_conflict') from exc
    raise exc


def _temporarily_unavailable(exc: Exception) -> NoReturn:
    raise HTTPException(status_code=503, detail='site_content_temporarily_unavailable') from exc


def _guard_form_request(request: Request, tenant: str) -> None:
    session_name = str(settings.SESSION_COOKIE_NAME or '')
    if session_name and request.cookies.get(session_name):
        csrf_name = str(settings.CSRF_COOKIE_NAME or '')
        cookie = request.cookies.get(csrf_name, '')
        header = request.headers.get('X-CSRF-Token', '')
        if not cookie or not header or not hmac.compare_digest(cookie, header):
            raise HTTPException(status_code=403, detail='csrf_failed')

    client_ip = request.client.host if request.client else 'unknown'
    _count, over, retry_after = rate_limit.incr_and_check_detailed(
        f'{tenant}:{client_ip}', 'public_form'
    )
    if over:
        raise HTTPException(
            status_code=429,
            detail='rate_limited',
            headers={'Retry-After': str(retry_after)},
        )


@router.get('/content', response_model=ContentPage)
def list_content(
    request: Request,
    service: SiteContentDependency,
    limit: PageLimit = 25,
    cursor: str | None = None,
):
    tenant = _tenant(request)
    try:
        return service.list_content(site_id=tenant, limit=limit, cursor=cursor)
    except ValueError as exc:
        _map_value_error(exc)
    except Exception as exc:
        _temporarily_unavailable(exc)


@router.get('/content/{content_type}/{slug}', response_model=ContentItem)
def get_content(
    request: Request,
    content_type: Slug,
    slug: Slug,
    service: SiteContentDependency,
):
    tenant = _tenant(request)
    try:
        item = service.get_content(site_id=tenant, content_type=content_type, slug=slug)
    except Exception as exc:
        _temporarily_unavailable(exc)
    if item is None:
        raise HTTPException(status_code=404, detail='content_not_found')
    return item


@router.get('/media/{asset_id}', response_model=MediaItem)
def get_media(request: Request, asset_id: UUID, service: SiteContentDependency):
    tenant = _tenant(request)
    try:
        item = service.get_media(site_id=tenant, asset_id=asset_id)
    except Exception as exc:
        _temporarily_unavailable(exc)
    if item is None:
        raise HTTPException(status_code=404, detail='media_not_found')
    return item


@router.get('/search', response_model=SearchPage)
def search(
    request: Request,
    service: SiteContentDependency,
    q: Annotated[str, Query(min_length=2, max_length=200)],
    limit: PageLimit = 25,
    cursor: str | None = None,
):
    tenant = _tenant(request)
    try:
        return service.search(site_id=tenant, query=q, limit=limit, cursor=cursor)
    except ValueError as exc:
        _map_value_error(exc)
    except Exception as exc:
        _temporarily_unavailable(exc)


@router.post('/forms/{form_key}', response_model=FormReceipt, status_code=status.HTTP_202_ACCEPTED)
def submit_form(
    request: Request,
    form_key: Slug,
    body: FormRequest,
    service: SiteContentDependency,
    replay_key: Annotated[
        str,
        Header(
            alias='Idempotency-Key', min_length=8, max_length=128, pattern=r'^[A-Za-z0-9._:-]+$'
        ),
    ],
):
    tenant = _tenant(request)
    _guard_form_request(request, tenant)
    try:
        return service.submit_form(
            site_id=tenant,
            form_key=form_key,
            replay_key=replay_key,
            payload=body.payload,
            consent=body.consent,
            request_id=getattr(
                request.state, 'request_id', request.headers.get('X-Request-Id', '')
            ),
        )
    except FormPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        _map_value_error(exc)
    except Exception as exc:
        _temporarily_unavailable(exc)
