"""Versioned, closed media-library API surface."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.middleware.tenant import require_tenant
from api.repositories.content_workspace import PostgresContentWorkspaceRepository
from api.repositories.media_library import PostgresMediaLibraryRepository
from api.security.request_auth import require_authenticated_principal
from api.security.identity import require_recent_reauthentication
from api.security.rate_limit import incr_and_check_tenant_detailed
from api.security.upload_capacity import (
    DownloadCapacityError,
    UploadBodyLimitError,
    UploadBodyTimeoutError,
    UploadCapacityError,
    download_delivery_slot,
    read_bounded_upload,
    upload_completion_slot,
)
from api.services.content_workspace_storage import ArtifactIntegrityError, configured_artifact_store
from api.services.media_library_policy import (
    DEFAULT_POLICY,
    FORMAT_RULES,
    delivery_headers,
    rule_for,
    validate_digest,
)
from api.settings import SITE_MANIFEST, settings


router = APIRouter(prefix='/media/v1', tags=['media-library'])
ASSET_STATES = {
    'pending',
    'uploaded',
    'inspecting',
    'accepted',
    'processing',
    'ready',
    'failed',
    'validated',
    'quarantined',
    'rejected',
    'archived',
    'deleted',
    'soft_deleted',
    'purge_planned',
}


def _camel(value: str) -> str:
    first, *rest = value.split('_')
    return first + ''.join(part.title() for part in rest)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True, alias_generator=_camel)


class UploadCreate(ContractModel):
    filename: str = Field(min_length=1, max_length=200)
    media_type: Literal[
        'image/jpeg',
        'image/png',
        'image/webp',
        'application/pdf',
        'audio/mpeg',
        'audio/ogg',
        'video/mp4',
        'video/webm',
    ]
    byte_size: int = Field(ge=1, le=100 * 1024 * 1024)
    sha256: str

    @model_validator(mode='after')
    def policy_valid(self):
        rule = rule_for(display_name=self.filename, claimed_type=self.media_type)
        validate_digest(self.sha256)
        if self.byte_size > min(rule.maximum_bytes, int(DEFAULT_POLICY['maximumObjectBytes'])):
            raise ValueError('media_quota_object_exceeded')
        return self


class MetadataUpdate(ContractModel):
    locale: str = Field(
        default='en', pattern=r'^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$', max_length=32
    )
    alt_text: str = Field(default='', max_length=500)
    decorative: bool = False
    caption: str = Field(default='', max_length=2_000)
    credit: str = Field(default='', max_length=500)
    license_code: str = Field(default='', pattern=r'^[A-Za-z0-9._-]{0,64}$')
    focal_x: float | None = Field(default=None, ge=0, le=1)
    focal_y: float | None = Field(default=None, ge=0, le=1)
    visibility: Literal['private', 'authenticated', 'public'] = 'private'

    @field_validator('alt_text', 'caption', 'credit')
    @classmethod
    def no_controls(cls, value: str) -> str:
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value):
            raise ValueError('media_metadata_invalid')
        return value

    @model_validator(mode='after')
    def focal_pair(self):
        if (self.focal_x is None) != (self.focal_y is None):
            raise ValueError('media_focal_point_invalid')
        if self.decorative and self.alt_text:
            raise ValueError('media_decorative_alt_conflict')
        return self


class LifecycleAction(ContractModel):
    target: Literal['archived', 'ready', 'soft_deleted']


class ExportCreate(ContractModel):
    output_format: Literal['json', 'csv']
    asset_ids: list[UUID] = Field(min_length=1, max_length=100)
    projection: list[
        Literal[
            'id',
            'filename',
            'mediaType',
            'byteSize',
            'sha256',
            'status',
            'visibility',
            'updatedAt',
        ]
    ] = Field(min_length=1, max_length=8)

    @field_validator('projection')
    @classmethod
    def unique_projection(cls, value):
        if len(value) != len(set(value)):
            raise ValueError('media_export_projection_invalid')
        return value

    @field_validator('asset_ids')
    @classmethod
    def unique_asset_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError('media_export_selection_invalid')
        return value


class CollectionCreate(ContractModel):
    title: str = Field(min_length=1, max_length=120)
    visibility: Literal['private', 'role_shared'] = 'private'
    shared_roles: list[Literal['owner', 'admin', 'editor', 'viewer']] = Field(
        default_factory=list, max_length=4
    )

    @model_validator(mode='after')
    def sharing_valid(self):
        if len(self.shared_roles) != len(set(self.shared_roles)):
            raise ValueError('media_collection_roles_invalid')
        if (self.visibility == 'private' and self.shared_roles) or (
            self.visibility == 'role_shared' and not self.shared_roles
        ):
            raise ValueError('media_collection_roles_invalid')
        return self


class CollectionAssets(ContractModel):
    asset_ids: list[UUID] = Field(min_length=1, max_length=100)

    @field_validator('asset_ids')
    @classmethod
    def unique_assets(cls, value):
        if len(value) != len(set(value)):
            raise ValueError('media_collection_assets_invalid')
        return value


def _collection_roles(request: Request, principal, tenant: str) -> list[str]:
    try:
        member = authorize(principal=principal, site_id=tenant, permission='media.read')
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='media_not_found') from exc
    role = member.get('role') if isinstance(member, dict) else None
    return [role] if role in {'owner', 'admin', 'editor', 'viewer'} else []


def get_repository() -> PostgresMediaLibraryRepository:
    return PostgresMediaLibraryRepository()


def get_artifact_store():
    return configured_artifact_store(
        root=settings.CONTENT_WORKSPACE_STORAGE_ROOT,
        encoded_key=settings.CONTENT_WORKSPACE_STORAGE_KEY or '',
        max_bytes=runtime_policy()['maximumObjectBytes'],
    )


def authorize(*, principal, site_id: str, permission: str):
    from api.repositories.identity_admin import require_permission

    return require_permission(user_id=principal.user_id, tenant_id=site_id, permission=permission)


def runtime_policy() -> dict:
    configured = SITE_MANIFEST.get('media', {})
    allowed = configured.get('allowedTypes', DEFAULT_POLICY['allowedTypes'])
    maximum = configured.get('maxBytes', DEFAULT_POLICY['maximumObjectBytes'])
    default_maximum = DEFAULT_POLICY.get('maximumObjectBytes')
    if (
        not isinstance(allowed, list)
        or not allowed
        or len(allowed) != len(set(allowed))
        or any(item not in FORMAT_RULES for item in allowed)
        or not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or not 1 <= maximum <= 100 * 1024 * 1024
        or not isinstance(default_maximum, int)
        or isinstance(default_maximum, bool)
    ):
        raise RuntimeError('media_policy_invalid')
    return {
        'allowedTypes': allowed,
        'maximumObjectBytes': min(maximum, default_maximum),
    }


def _authorized_scope(request: Request, permission: str):
    principal = require_authenticated_principal(request)
    tenant = require_tenant(request)
    try:
        authorize(principal=principal, site_id=tenant, permission=permission)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='media_not_found') from exc
    return principal, tenant


def _sensitive_guard(request: Request, principal) -> None:
    if not principal.recently_authenticated:
        raise HTTPException(status_code=401, detail='recent_reauthentication_required')
    try:
        require_recent_reauthentication(authenticated_at=principal.authenticated_at)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail='recent_reauthentication_required') from exc
    session_name = str(settings.SESSION_COOKIE_NAME or '')
    if session_name and request.cookies.get(session_name):
        csrf_name = str(settings.CSRF_COOKIE_NAME or '')
        cookie = request.cookies.get(csrf_name, '')
        header = request.headers.get('X-CSRF-Token', '')
        if not cookie or not header or not hmac.compare_digest(cookie, header):
            raise HTTPException(status_code=403, detail='csrf_failed')


def _expected_version(value: str) -> int:
    version = value.strip().strip('"')
    if not version.isdigit() or int(version) < 1:
        raise HTTPException(status_code=422, detail='media_expected_version_invalid')
    return int(version)


def _cursor_key() -> bytes:
    value = str(settings.JWT_SECRET or '')
    if len(value) < 32:
        raise RuntimeError('media_cursor_key_invalid')
    return value.encode()


def _cursor_scope(*, tenant: str, state: str | None, media_type: str | None, search: str | None) -> str:
    return hashlib.sha256(
        json.dumps(
            {'tenant': tenant, 'state': state, 'mediaType': media_type, 'search': search},
            sort_keys=True,
            separators=(',', ':'),
        ).encode()
    ).hexdigest()


def _encode_cursor(anchor: dict, *, scope: str) -> str:
    body = json.dumps({**anchor, 'scope': scope}, sort_keys=True, separators=(',', ':')).encode()
    signature = hmac.new(_cursor_key(), body, hashlib.sha256).digest()
    return urlsafe_b64encode(body + signature).decode().rstrip('=')


def _decode_cursor(value: str, *, expected_scope: str) -> tuple[datetime, UUID]:
    try:
        raw = urlsafe_b64decode(value + '=' * (-len(value) % 4))
        body, signature = raw[:-32], raw[-32:]
        if not hmac.compare_digest(signature, hmac.new(_cursor_key(), body, hashlib.sha256).digest()):
            raise ValueError
        payload = json.loads(body)
        if set(payload) != {'id', 'scope', 'updatedAt'} or not hmac.compare_digest(
            str(payload['scope']), expected_scope
        ):
            raise ValueError
        updated_at = datetime.fromisoformat(payload['updatedAt'])
        identifier = UUID(payload['id'])
        if updated_at.tzinfo is None:
            raise ValueError
        return updated_at, identifier
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail='media_cursor_invalid') from exc


def _map_operation_error(exc: ValueError) -> HTTPException:
    code = str(exc)
    if code == 'media_not_found':
        return HTTPException(status_code=404, detail=code)
    if code in {'media_version_conflict', 'media_idempotency_conflict'}:
        return HTTPException(status_code=409, detail=code)
    if code == 'media_transition_blocked':
        return HTTPException(status_code=423, detail=code)
    return HTTPException(status_code=422, detail=code)


@router.get('/capabilities')
def capabilities(request: Request):
    _authorized_scope(request, 'media.read')
    policy = runtime_policy()
    return {
        'schemaVersion': 1,
        'formats': [
            {
                'mediaType': rule.media_type,
                'extensions': list(rule.extensions),
                'delivery': rule.delivery,
            }
            for rule in FORMAT_RULES.values()
            if rule.media_type in policy['allowedTypes']
        ],
        'limits': {
            'maximumObjectBytes': policy['maximumObjectBytes'],
            'maximumBatchFiles': DEFAULT_POLICY['maximumBatchFiles'],
            'maximumBatchBytes': DEFAULT_POLICY['maximumBatchBytes'],
        },
    }


@router.get('/assets')
def list_assets(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    state: str | None = Query(default=None, max_length=24),
    media_type: str | None = Query(default=None, max_length=127),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    cursor: str | None = Query(default=None, min_length=40, max_length=512),
):
    principal, tenant = _authorized_scope(request, 'media.read')
    if state and state not in ASSET_STATES:
        raise HTTPException(status_code=422, detail='media_filter_invalid')
    if media_type and media_type not in FORMAT_RULES:
        raise HTTPException(status_code=422, detail='media_filter_invalid')
    if cursor and offset:
        raise HTTPException(status_code=422, detail='media_cursor_invalid')
    scope = _cursor_scope(tenant=tenant, state=state, media_type=media_type, search=search)
    cursor_after = _decode_cursor(cursor, expected_scope=scope) if cursor else None
    try:
        result = get_repository().list_assets(
            site_id=tenant,
            actor_ref=f'user:{principal.user_id}',
            limit=limit,
            offset=offset,
            state=state,
            media_type=media_type,
            search=search,
            cursor_after=cursor_after,
        )
        anchor = result.pop('nextAnchor', None)
        result['nextCursor'] = _encode_cursor(anchor, scope=scope) if anchor else None
        return result
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.get('/assets/{asset_id}')
def get_asset(asset_id: UUID, request: Request):
    principal, tenant = _authorized_scope(request, 'media.read')
    try:
        return get_repository().get_asset(
            site_id=tenant, asset_id=asset_id, actor_ref=f'user:{principal.user_id}'
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='media_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.post('/uploads', status_code=201)
def create_upload(
    payload: UploadCreate,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias='Idempotency-Key',
            min_length=8,
            max_length=128,
            pattern=r'^[A-Za-z0-9._:-]+$',
        ),
    ],
):
    principal, tenant = _authorized_scope(request, 'media.upload')
    try:
        _count, limited, retry_after = incr_and_check_tenant_detailed(
            tenant, str(principal.user_id), 'media_upload_create'
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_rate_limit_unavailable') from exc
    if limited:
        raise HTTPException(
            status_code=429,
            detail='media_rate_limit_exceeded',
            headers={'Retry-After': str(retry_after)},
        )
    policy = runtime_policy()
    if (
        payload.media_type not in policy['allowedTypes']
        or payload.byte_size > policy['maximumObjectBytes']
    ):
        raise HTTPException(status_code=422, detail='media_policy_rejected')
    try:
        return PostgresContentWorkspaceRepository().create_asset_upload(
            site_id=tenant,
            owner_ref=f'user:{principal.user_id}',
            payload=payload.model_dump(),
            idempotency_key=idempotency_key,
            maximum_stored_bytes=max(1024 * 1024 * 1024, policy['maximumObjectBytes'] * 20),
            maximum_active_uploads=100,
            maximum_pending_processing=200,
        )
    except ValueError as exc:
        code = str(exc).replace('content_', 'media_')
        raise HTTPException(
            status_code=409 if code == 'media_idempotency_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.put('/assets/{asset_id}/content')
async def complete_upload(
    asset_id: UUID,
    request: Request,
    upload_grant: Annotated[str, Header(alias='Upload-Grant', min_length=32, max_length=4096)],
):
    principal, tenant = _authorized_scope(request, 'media.upload')
    maximum = runtime_policy()['maximumObjectBytes']
    try:
        _count, limited, retry_after = incr_and_check_tenant_detailed(
            tenant, str(principal.user_id), 'media_upload_complete'
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_rate_limit_unavailable') from exc
    if limited:
        raise HTTPException(
            status_code=429,
            detail='media_rate_limit_exceeded',
            headers={'Retry-After': str(retry_after)},
        )
    repository = PostgresContentWorkspaceRepository()
    try:
        admission = repository.validate_asset_upload_grant(
            site_id=tenant,
            asset_id=asset_id,
            owner_ref=f'user:{principal.user_id}',
            upload_grant=upload_grant,
        )
        length = request.headers.get('content-length')
        if length is not None and (
            not length.isdigit() or int(length) != admission['expectedBytes']
        ):
            raise HTTPException(status_code=422, detail='media_integrity_failed')
        async with upload_completion_slot():
            content = await read_bounded_upload(
                request.stream(), maximum_bytes=min(maximum, admission['expectedBytes'])
            )
            return repository.complete_asset_upload(
                site_id=tenant,
                asset_id=asset_id,
                owner_ref=f'user:{principal.user_id}',
                upload_grant=upload_grant,
                content=content,
                artifact_store=get_artifact_store(),
                maximum_bytes=maximum,
            )
    except UploadCapacityError as exc:
        raise HTTPException(
            status_code=429,
            detail='media_upload_capacity_exhausted',
            headers={'Retry-After': '2'},
        ) from exc
    except UploadBodyLimitError as exc:
        raise HTTPException(status_code=413, detail='media_quota_object_exceeded') from exc
    except UploadBodyTimeoutError as exc:
        raise HTTPException(status_code=408, detail='media_upload_timeout') from exc
    except HTTPException:
        raise
    except (ValueError, ArtifactIntegrityError) as exc:
        code = str(exc)
        status_code = 404 if code == 'content_not_found' else 422
        raise HTTPException(
            status_code=status_code, detail=code.replace('content_', 'media_')
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.get('/assets/{asset_id}/content')
async def read_content(
    asset_id: UUID,
    request: Request,
    download_grant: Annotated[str, Header(alias='Download-Grant', min_length=32, max_length=4096)],
):
    principal, tenant = _authorized_scope(request, 'media.read')
    try:
        try:
            _count, limited, retry_after = incr_and_check_tenant_detailed(
                tenant, str(principal.user_id), 'media_download'
            )
            if not limited:
                _count, limited, retry_after = incr_and_check_tenant_detailed(
                    tenant, 'tenant-aggregate', 'media_download_tenant'
                )
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail='media_rate_limit_unavailable'
            ) from exc
        if limited:
            raise HTTPException(
                status_code=429,
                detail='media_rate_limit_exceeded',
                headers={'Retry-After': str(retry_after)},
            )
        async with download_delivery_slot():
            result = await asyncio.to_thread(
                PostgresContentWorkspaceRepository().read_asset_content,
                site_id=tenant,
                asset_id=asset_id,
                requester_ref=f'user:{principal.user_id}',
                download_grant=download_grant,
                artifact_store=get_artifact_store(),
            )
        headers = delivery_headers(
            media_type=result['media_type'],
            inline_safe_derivative=result['media_type'].startswith('image/'),
        )
        headers['X-Content-SHA256'] = result['sha256']
        return Response(content=result['content'], media_type=result['media_type'], headers=headers)
    except DownloadCapacityError as exc:
        raise HTTPException(
            status_code=429,
            detail='media_download_capacity_exhausted',
            headers={'Retry-After': '1'},
        ) from exc
    except HTTPException:
        raise
    except (ValueError, ArtifactIntegrityError) as exc:
        code = str(exc)
        status_code = 404 if code == 'content_not_found' else 422
        raise HTTPException(
            status_code=status_code, detail=code.replace('content_', 'media_')
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.put('/assets/{asset_id}/metadata')
def update_metadata(
    asset_id: UUID,
    payload: MetadataUpdate,
    request: Request,
    if_match: Annotated[str, Header(alias='If-Match', min_length=1, max_length=32)],
):
    principal, tenant = _authorized_scope(request, 'media.write')
    _sensitive_guard(request, principal)
    version = _expected_version(if_match)
    try:
        return get_repository().update_metadata(
            site_id=tenant,
            asset_id=asset_id,
            actor_ref=f'user:{principal.user_id}',
            expected_version=version,
            payload=payload.model_dump(by_alias=True),
        )
    except ValueError as exc:
        code = str(exc)
        status = (
            409 if code == 'media_version_conflict' else 404 if code == 'media_not_found' else 422
        )
        raise HTTPException(status_code=status, detail=code) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.get('/assets/{asset_id}/references')
def list_references(asset_id: UUID, request: Request):
    principal, tenant = _authorized_scope(request, 'media.read')
    try:
        return get_repository().list_references(
            site_id=tenant, asset_id=asset_id, actor_ref=f'user:{principal.user_id}'
        )
    except ValueError as exc:
        raise _map_operation_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.get('/assets/{asset_id}/destructive-preview')
def get_destructive_preview(asset_id: UUID, request: Request):
    principal, tenant = _authorized_scope(request, 'media.delete')
    _sensitive_guard(request, principal)
    try:
        return get_repository().destructive_preview(
            site_id=tenant, asset_id=asset_id, actor_ref=f'user:{principal.user_id}'
        )
    except ValueError as exc:
        raise _map_operation_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.post('/assets/{asset_id}/lifecycle')
def transition_asset(
    asset_id: UUID,
    payload: LifecycleAction,
    request: Request,
    if_match: Annotated[str, Header(alias='If-Match', min_length=1, max_length=32)],
    idempotency_key: Annotated[
        str,
        Header(
            alias='Idempotency-Key',
            min_length=8,
            max_length=128,
            pattern=r'^[A-Za-z0-9._:-]+$',
        ),
    ],
):
    permission = 'media.archive' if payload.target in {'archived', 'ready'} else 'media.delete'
    principal, tenant = _authorized_scope(request, permission)
    _sensitive_guard(request, principal)
    try:
        return get_repository().transition_asset(
            site_id=tenant,
            asset_id=asset_id,
            actor_ref=f'user:{principal.user_id}',
            target=payload.target,
            expected_version=_expected_version(if_match),
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise _map_operation_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.post('/exports', status_code=202)
def create_export(
    payload: ExportCreate,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias='Idempotency-Key',
            min_length=8,
            max_length=128,
            pattern=r'^[A-Za-z0-9._:-]+$',
        ),
    ],
):
    principal, tenant = _authorized_scope(request, 'media.read')
    _sensitive_guard(request, principal)
    try:
        _count, limited, retry_after = incr_and_check_tenant_detailed(
            tenant, str(principal.user_id), 'media_export_create'
        )
        if not limited:
            _count, limited, retry_after = incr_and_check_tenant_detailed(
                tenant, 'tenant-aggregate', 'media_export_tenant'
            )
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_rate_limit_unavailable') from exc
    if limited:
        raise HTTPException(
            status_code=429,
            detail='media_rate_limit_exceeded',
            headers={'Retry-After': str(retry_after)},
        )
    request_digest = hashlib.sha256(
        json.dumps(
            {
                'format': payload.output_format,
                'assetIds': sorted(str(asset_id) for asset_id in payload.asset_ids),
                'projection': payload.projection,
                'idempotencyKey': idempotency_key,
            },
            sort_keys=True,
            separators=(',', ':'),
        ).encode()
    ).hexdigest()
    try:
        return get_repository().create_export(
            site_id=tenant,
            actor_ref=f'user:{principal.user_id}',
            output_format=payload.output_format,
            projection={
                'fields': [str(field) for field in payload.projection],
                'assetIds': sorted(str(asset_id) for asset_id in payload.asset_ids),
                'filters': {},
            },
            request_digest=request_digest,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            maximum_outstanding=10,
        )
    except ValueError as exc:
        if str(exc) == 'media_export_capacity_exceeded':
            raise HTTPException(
                status_code=429,
                detail='media_export_capacity_exceeded',
                headers={'Retry-After': '60'},
            ) from exc
        raise _map_operation_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.get('/collections')
def list_collections(request: Request):
    principal, tenant = _authorized_scope(request, 'media.read')
    try:
        return get_repository().list_collections(
            site_id=tenant,
            actor_ref=f'user:{principal.user_id}',
            roles=_collection_roles(request, principal, tenant),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.post('/collections', status_code=201)
def create_collection(payload: CollectionCreate, request: Request):
    principal, tenant = _authorized_scope(request, 'media.write')
    _sensitive_guard(request, principal)
    try:
        return get_repository().create_collection(
            site_id=tenant,
            actor_ref=f'user:{principal.user_id}',
            title=payload.title.strip(),
            visibility=payload.visibility,
            shared_roles=list(payload.shared_roles),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.post('/collections/{collection_id}/assets')
def add_collection_assets(collection_id: UUID, payload: CollectionAssets, request: Request):
    principal, tenant = _authorized_scope(request, 'media.write')
    _sensitive_guard(request, principal)
    try:
        return get_repository().add_collection_assets(
            site_id=tenant,
            actor_ref=f'user:{principal.user_id}',
            roles=_collection_roles(request, principal, tenant),
            collection_id=collection_id,
            asset_ids=payload.asset_ids,
        )
    except ValueError as exc:
        raise _map_operation_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.get('/jobs')
def list_jobs(
    request: Request,
    asset_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
):
    principal, tenant = _authorized_scope(request, 'media.read')
    try:
        return get_repository().list_jobs(
            site_id=tenant,
            actor_ref=f'user:{principal.user_id}',
            asset_id=asset_id,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.post('/jobs/{job_id}/retry')
def retry_job(job_id: UUID, request: Request):
    principal, tenant = _authorized_scope(request, 'media.write')
    _sensitive_guard(request, principal)
    try:
        return get_repository().retry_job(
            site_id=tenant, job_id=job_id, actor_ref=f'user:{principal.user_id}'
        )
    except ValueError as exc:
        code = str(exc)
        status = 409 if code == 'media_job_retry_blocked' else 404
        raise HTTPException(status_code=status, detail=code) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc


@router.get('/exports/{export_id}')
def get_export(export_id: UUID, request: Request):
    principal, tenant = _authorized_scope(request, 'media.read')
    try:
        return get_repository().get_export(
            site_id=tenant, export_id=export_id, actor_ref=f'user:{principal.user_id}'
        )
    except ValueError as exc:
        raise _map_operation_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='media_dependency_unavailable') from exc
