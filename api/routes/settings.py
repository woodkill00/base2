from __future__ import annotations

import zoneinfo
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from api.auth.repo import insert_audit_event
from api.middleware.tenant import require_tenant
from api.repositories import settings as repository
from api.security.request_auth import require_authenticated_principal
from api.settings import SITE_MANIFEST

router = APIRouter(prefix='/settings', tags=['settings'])


class PreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0)
    theme: Literal['system', 'light', 'dark']
    contrast: Literal['system', 'standard', 'high']
    motion: Literal['system', 'full', 'reduced']
    density: Literal['comfortable', 'compact']
    locale: str = Field(min_length=2, max_length=32)
    timezone: str = Field(min_length=1, max_length=255)
    week_start: Literal['system', 'monday', 'sunday', 'saturday']


class NotificationChoice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_family: Literal['security', 'transactional', 'product', 'marketing']
    channel: Literal['email', 'in_app', 'browser']
    delivery: Literal['immediate', 'digest', 'disabled']


class NotificationUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    preferences: list[NotificationChoice] = Field(max_length=12)


def _principal_and_tenant(request: Request):
    return require_authenticated_principal(request), require_tenant(request)


def _accounts_enabled() -> bool:
    return any(item.get('id') == 'accounts' and item.get('enabled') for item in SITE_MANIFEST['modules'])


@router.get('/capabilities')
async def capabilities(request: Request):
    _principal_and_tenant(request)
    categories = [
        {'id': 'overview', 'path': '/settings', 'version': 'v1'},
        {'id': 'profile', 'path': '/settings/profile', 'version': 'v1'},
        {'id': 'security', 'path': '/settings/security', 'version': 'v1'},
        {'id': 'privacy', 'path': '/settings/privacy', 'version': 'v1'},
        {'id': 'notifications', 'path': '/settings/notifications', 'version': 'v1'},
        {'id': 'appearance', 'path': '/settings/appearance', 'version': 'v1'},
        {'id': 'language-region', 'path': '/settings/language-region', 'version': 'v1'},
    ]
    if _accounts_enabled():
        categories.extend([
            {'id': 'organization', 'path': '/settings/organization', 'version': 'v1'},
            {'id': 'developer', 'path': '/settings/developer', 'version': 'v1'},
        ])
    return {'schema_version': 1, 'categories': categories}


@router.get('/preferences')
async def preferences(request: Request):
    principal, tenant_id = _principal_and_tenant(request)
    return repository.get_preferences(user_id=principal.user_id, tenant_id=tenant_id)


@router.put('/preferences')
async def put_preferences(payload: PreferenceUpdate, request: Request):
    principal, tenant_id = _principal_and_tenant(request)
    if payload.locale not in SITE_MANIFEST['locales']:
        raise HTTPException(status_code=422, detail='settings_locale_invalid')
    if payload.timezone not in zoneinfo.available_timezones():
        raise HTTPException(status_code=422, detail='settings_timezone_invalid')
    values = payload.model_dump(exclude={'expected_version'})
    result = repository.update_preferences(
        user_id=principal.user_id, tenant_id=tenant_id,
        expected_version=payload.expected_version, values=values,
    )
    if result is None:
        raise HTTPException(status_code=409, detail='settings_version_conflict')
    insert_audit_event(
        user_id=principal.user_id, action='user.preferences_updated',
        ip=request.client.host if request.client else '',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'tenant_id': tenant_id, 'version': result['version']},
    )
    return result


def _notification_payload(choices: list[NotificationChoice]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    result = []
    for choice in choices:
        key = (choice.event_family, choice.channel)
        if key in seen:
            raise HTTPException(status_code=422, detail='settings_notification_duplicate')
        seen.add(key)
        mandatory = choice.event_family in {'security', 'transactional'}
        if mandatory and choice.delivery == 'disabled':
            raise HTTPException(status_code=422, detail='settings_notification_mandatory')
        result.append({**choice.model_dump(), 'mandatory': mandatory})
    return result


@router.get('/notifications')
async def notifications(request: Request):
    principal, tenant_id = _principal_and_tenant(request)
    return {'preferences': repository.list_notifications(user_id=principal.user_id, tenant_id=tenant_id)}


@router.put('/notifications')
async def put_notifications(payload: NotificationUpdate, request: Request):
    principal, tenant_id = _principal_and_tenant(request)
    values = _notification_payload(payload.preferences)
    saved = repository.replace_notifications(
        user_id=principal.user_id, tenant_id=tenant_id, preferences=values
    )
    insert_audit_event(
        user_id=principal.user_id, action='user.notification_preferences_updated',
        ip=request.client.host if request.client else '',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'tenant_id': tenant_id, 'preference_count': len(saved)},
    )
    return {'preferences': saved}


@router.get('/security-events')
async def get_security_events(request: Request, limit: int = 25):
    principal, _ = _principal_and_tenant(request)
    return {'events': repository.security_events(user_id=principal.user_id, limit=limit)}
