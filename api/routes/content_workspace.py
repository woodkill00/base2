from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Header, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.middleware.tenant import require_tenant
from api.repositories.content_workspace import PostgresContentWorkspaceRepository
from api.security.request_auth import require_authenticated_principal
from api.services.content_workspace_media import MAX_UPLOAD_BYTES
from api.services.content_workspace_transfer import MAX_BYTES as MAX_IMPORT_BYTES
from api.services.content_workspace_storage import (
    ArtifactIntegrityError,
    configured_artifact_store,
)
from api.settings import SITE_MANIFEST, settings


router = APIRouter(prefix='/content/v1', tags=['content-workspace'])

FIELD_KINDS = (
    'short_text',
    'long_text',
    'rich_text',
    'integer',
    'decimal',
    'boolean',
    'date',
    'datetime',
    'enum',
    'slug',
    'url',
    'email',
    'location',
    'reference',
    'references',
    'image',
    'file',
    'json_object',
)
IDENTIFIER = re.compile(r'^[a-z][a-z0-9_]{1,62}$')


def get_artifact_store():
    return configured_artifact_store(
        root=settings.CONTENT_WORKSPACE_STORAGE_ROOT,
        encoded_key=settings.CONTENT_WORKSPACE_STORAGE_KEY or '',
    )


def _camel(value: str) -> str:
    first, *rest = value.split('_')
    return first + ''.join(part.title() for part in rest)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True, alias_generator=_camel)


class FieldDefinition(ContractModel):
    field_key: str = Field(min_length=2, max_length=63)
    label: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2_000)
    field_kind: Literal[
        'short_text',
        'long_text',
        'rich_text',
        'integer',
        'decimal',
        'boolean',
        'date',
        'datetime',
        'enum',
        'slug',
        'url',
        'email',
        'location',
        'reference',
        'references',
        'image',
        'file',
        'json_object',
    ]
    required: bool = False
    nullable: bool = False
    default_value: str | int | bool | None = None
    validation: dict = Field(default_factory=dict)
    presentation: dict = Field(default_factory=dict)
    indexed: bool = False
    unique: bool = False
    read_permission: str = 'content.read'
    write_permission: str = 'content.write'

    @field_validator('field_key')
    @classmethod
    def safe_key(cls, value: str) -> str:
        if not IDENTIFIER.fullmatch(value):
            raise ValueError('content_identifier_invalid')
        return value

    @field_validator('validation')
    @classmethod
    def closed_validation(cls, value: dict) -> dict:
        allowed = {
            'minLength',
            'maxLength',
            'minimum',
            'maximum',
            'decimalPlaces',
            'choices',
            'maximumItems',
            'maximumDepth',
            'targetType',
            'deletionPolicy',
        }
        if len(value) > 32 or set(value) - allowed:
            raise ValueError('field_validation_key_invalid')
        return value


class DefinitionCreate(ContractModel):
    type_key: str = Field(min_length=2, max_length=63)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2_000)
    preset_id: str = Field(default='custom', min_length=2, max_length=63)
    fields: list[FieldDefinition] = Field(default_factory=list, max_length=64)

    @field_validator('type_key', 'preset_id')
    @classmethod
    def safe_identifier(cls, value: str) -> str:
        if not IDENTIFIER.fullmatch(value):
            raise ValueError('content_identifier_invalid')
        return value


class RecordCreate(ContractModel):
    slug: str = Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    values: dict = Field(default_factory=dict)

    @field_validator('values')
    @classmethod
    def bounded_values(cls, value: dict) -> dict:
        if len(value) > 128 or any(not IDENTIFIER.fullmatch(str(key)) for key in value):
            raise ValueError('record_values_invalid')
        return value


class RecordUpdate(ContractModel):
    values: dict
    expected_version: int | None = Field(default=None, ge=1)

    @field_validator('values')
    @classmethod
    def bounded_values(cls, value: dict) -> dict:
        return RecordCreate.bounded_values(value)


class TransitionRequest(ContractModel):
    expected_version: int = Field(ge=1)
    publish_at: datetime | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode='after')
    def valid_schedule_metadata(self):
        if (self.publish_at is None) != (self.timezone is None):
            raise ValueError('content_schedule_metadata_invalid')
        if self.publish_at is not None:
            if self.publish_at.tzinfo is None or self.publish_at <= datetime.now(UTC):
                raise ValueError('content_schedule_time_invalid')
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, ValueError, TypeError):
                raise ValueError('schedule_timezone_invalid') from None
        return self


class DefinitionMutation(ContractModel):
    expected_lock_version: int = Field(ge=1)
    confirm_lossy: bool = False


class FilterRule(ContractModel):
    field: str = Field(min_length=2, max_length=63)
    operator: Literal[
        'eq', 'ne', 'contains', 'starts_with', 'in', 'lt', 'lte', 'gt', 'gte', 'is_null'
    ]
    value: str | int | bool | list[str] | None


class QueryDescription(ContractModel):
    filters: list[FilterRule] = Field(default_factory=list, max_length=16)
    sort: list[str] = Field(default_factory=lambda: ['slug'], max_length=3)
    fields: list[str] = Field(default_factory=list, max_length=64)
    expand: list[str] = Field(default_factory=list, max_length=4)
    limit: int = Field(default=25, ge=1, le=100)


class SavedViewCreate(ContractModel):
    title: str = Field(min_length=1, max_length=120)
    query: QueryDescription
    visibility: Literal['private', 'role_shared'] = 'private'
    shared_roles: list[Literal['owner', 'admin', 'editor', 'viewer']] = Field(
        default_factory=list, max_length=4
    )

    @field_validator('shared_roles')
    @classmethod
    def distinct_roles(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError('saved_view_roles_invalid')
        return value


class SavedViewUpdate(ContractModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    query: QueryDescription | None = None
    visibility: Literal['private', 'role_shared'] | None = None
    shared_roles: list[Literal['owner', 'admin', 'editor', 'viewer']] | None = Field(
        default=None, max_length=4
    )
    expected_version: int | None = Field(default=None, ge=1)

    @field_validator('shared_roles')
    @classmethod
    def distinct_roles(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError('saved_view_roles_invalid')
        return value

    @model_validator(mode='after')
    def has_mutation(self):
        if all(
            value is None for value in (self.title, self.query, self.visibility, self.shared_roles)
        ):
            raise ValueError('saved_view_update_empty')
        return self


class RestoreRequest(ContractModel):
    expected_version: int = Field(ge=1)


class ImportCreate(ContractModel):
    format: Literal['json', 'csv'] = 'json'
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    schema_version: int = Field(ge=1)
    mapping: dict[str, str] = Field(default_factory=dict)
    duplicate_policy: Literal['review', 'skip_exact', 'update_exact'] = 'review'
    atomic_policy: Literal['all_or_nothing', 'valid_rows'] = 'all_or_nothing'

    @field_validator('mapping')
    @classmethod
    def bounded_mapping(cls, value: dict[str, str]) -> dict[str, str]:
        if (
            len(value) > 128
            or any(not key or len(key) > 120 for key in value)
            or any(not IDENTIFIER.fullmatch(target) for target in value.values())
        ):
            raise ValueError('content_schema_invalid')
        return value


class ExportCreate(ContractModel):
    format: Literal['json', 'csv'] = 'json'
    schema_version: int = Field(ge=1)
    fields: list[str] = Field(default_factory=list, max_length=64)

    @field_validator('fields')
    @classmethod
    def bounded_fields(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(not IDENTIFIER.fullmatch(item) for item in value):
            raise ValueError('content_schema_invalid')
        return value


class AssetUploadCreate(ContractModel):
    filename: str = Field(min_length=1, max_length=200)
    media_type: Literal['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
    byte_size: int = Field(ge=1, le=10 * 1024 * 1024)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

    @field_validator('filename')
    @classmethod
    def safe_filename(cls, value: str) -> str:
        if (
            '/' in value
            or '\\' in value
            or value in {'.', '..'}
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._ -]{0,199}', value)
        ):
            raise ValueError('content_media_filename_invalid')
        return value


class AssetBindingCreate(ContractModel):
    asset_id: UUID
    expected_version: int = Field(ge=1)
    alt_text: str = Field(default='', max_length=500)
    caption: str = Field(default='', max_length=2_000)
    credit: str = Field(default='', max_length=500)
    order: int = Field(default=0, ge=0, le=50)
    focal_x: float | None = Field(default=None, ge=0, le=1)
    focal_y: float | None = Field(default=None, ge=0, le=1)


class RelationshipCreate(ContractModel):
    field_key: str = Field(min_length=2, max_length=63)
    target_id: UUID
    expected_version: int = Field(ge=1)
    order: int = Field(default=0, ge=0, le=50)
    deletion_policy: Literal['restrict', 'detach', 'cascade_soft'] = 'restrict'

    @field_validator('field_key')
    @classmethod
    def safe_field_key(cls, value: str) -> str:
        if not IDENTIFIER.fullmatch(value):
            raise ValueError('content_identifier_invalid')
        return value


TRANSITION_ACTIONS = {
    'submit_review',
    'return_draft',
    'schedule',
    'publish',
    'archive',
    'restore',
    'delete',
}
TRANSITION_PERMISSIONS = {
    'submit_review': 'content-workspace.write',
    'return_draft': 'content-workspace.write',
    'schedule': 'content-workspace.schedule',
    'publish': 'content-workspace.publish',
    'archive': 'content-workspace.publish',
    'restore': 'content-workspace.write',
    'delete': 'content-workspace.delete',
}


def get_repository() -> PostgresContentWorkspaceRepository:
    return PostgresContentWorkspaceRepository()


def workspace_enabled() -> bool:
    return any(
        item.get('id') == 'content-workspace' and item.get('enabled') is True
        for item in SITE_MANIFEST.get('modules', [])
    )


def _scope(request: Request):
    if not workspace_enabled():
        raise HTTPException(status_code=404, detail='content_capability_disabled')
    principal = require_authenticated_principal(request)
    tenant = require_tenant(request)
    return principal, tenant


def authorize(*, principal, site_id: str, permission: str):
    from api.repositories.identity_admin import require_permission

    try:
        return require_permission(
            user_id=principal.user_id, tenant_id=site_id, permission=permission
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc


def _authorized_scope(request: Request, permission: str):
    principal, tenant = _scope(request)
    membership = authorize(principal=principal, site_id=tenant, permission=permission)
    request.state.content_workspace_role = membership.get('role') if membership else None
    return principal, tenant


def _expected_version(if_match: str | None, body_version: int | None = None) -> int:
    if body_version is not None:
        return body_version
    if not if_match:
        raise HTTPException(status_code=428, detail='content_expected_version_required')
    candidate = if_match.strip().strip('"')
    if not candidate.isdigit() or int(candidate) < 1:
        raise HTTPException(status_code=422, detail='content_expected_version_invalid')
    return int(candidate)


def _valid_type_key(type_key: str) -> None:
    if not IDENTIFIER.fullmatch(type_key):
        raise HTTPException(status_code=422, detail='content_identifier_invalid')


@router.get('/capabilities')
def capabilities(request: Request):
    _scope(request)
    return {
        'schemaVersion': 1,
        'fieldKinds': list(FIELD_KINDS),
        'workflowStates': ['draft', 'in_review', 'scheduled', 'published', 'archived', 'deleted'],
        'presets': [
            'article',
            'catalog',
            'rental',
            'portfolio',
            'documentation',
            'listing',
            'event',
            'community',
        ],
        'limits': {
            'maximumFields': 64,
            'maximumFilters': 16,
            'maximumPageSize': 100,
            'maximumRelationshipDepth': 2,
        },
    }


@router.get('/types')
def list_types(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = Query(default=None, min_length=16, max_length=2_048),
):
    _, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().list_definitions(site_id=tenant, limit=limit, cursor=cursor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types', status_code=status.HTTP_201_CREATED)
def create_type(payload: DefinitionCreate, request: Request):
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().create_definition(
            site_id=tenant,
            actor_ref=f'user:{principal.user_id}',
            payload=payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/versions/{version}')
def get_type(type_key: str, version: Annotated[int, Path(ge=1)], request: Request):
    _valid_type_key(type_key)
    _, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().get_definition(site_id=tenant, type_key=type_key, version=version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/versions/{version}/preview')
def preview_type(type_key: str, version: Annotated[int, Path(ge=1)], request: Request):
    _valid_type_key(type_key)
    _, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().preview_definition(
            site_id=tenant, type_key=type_key, version=version
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/versions/{version}/publish')
def publish_type(
    type_key: str,
    version: Annotated[int, Path(ge=1)],
    payload: DefinitionMutation,
    request: Request,
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().publish_definition(
            site_id=tenant,
            type_key=type_key,
            version=version,
            expected_lock_version=payload.expected_lock_version,
            confirm_lossy=payload.confirm_lossy,
            actor_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=409 if 'conflict' in code else 422, detail=code) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/versions/{version}/retire')
def retire_type(
    type_key: str,
    version: Annotated[int, Path(ge=1)],
    payload: DefinitionMutation,
    request: Request,
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().retire_definition(
            site_id=tenant,
            type_key=type_key,
            version=version,
            expected_lock_version=payload.expected_lock_version,
            actor_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=409 if 'conflict' in code else 422, detail=code) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/records')
def list_records(
    type_key: str,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = Query(default=None, min_length=16, max_length=2_048),
    q: str | None = Query(default=None, max_length=8_192),
):
    _, tenant = _authorized_scope(request, 'content-workspace.read')
    _valid_type_key(type_key)
    query = QueryDescription().model_dump()
    if q:
        try:
            query = QueryDescription.model_validate(json.loads(q)).model_dump()
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail='content_query_invalid') from exc
    query['limit'] = min(query['limit'], limit)
    try:
        return get_repository().list_records(
            site_id=tenant,
            type_key=type_key,
            limit=query['limit'],
            cursor=cursor,
            query=query,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/records', status_code=status.HTTP_201_CREATED)
def create_record(type_key: str, payload: RecordCreate, request: Request):
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    _valid_type_key(type_key)
    try:
        return get_repository().create_record(
            site_id=tenant,
            type_key=type_key,
            actor_ref=f'user:{principal.user_id}',
            payload=payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.patch('/types/{type_key}/records/{record_id}')
def update_record(
    type_key: str,
    record_id: UUID,
    payload: RecordUpdate,
    request: Request,
    if_match: Annotated[str | None, Header(alias='If-Match')] = None,
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    expected = _expected_version(if_match, payload.expected_version)
    try:
        return get_repository().update_record(
            site_id=tenant,
            type_key=type_key,
            record_id=record_id,
            expected_version=expected,
            actor_ref=f'user:{principal.user_id}',
            values=payload.values,
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/records/{record_id}/transitions/{action}')
def transition_record(
    type_key: str,
    record_id: UUID,
    action: str,
    payload: TransitionRequest,
    request: Request,
):
    _valid_type_key(type_key)
    if action not in TRANSITION_ACTIONS:
        raise HTTPException(status_code=422, detail='content_transition_invalid')
    principal, tenant = _authorized_scope(request, TRANSITION_PERMISSIONS[action])
    try:
        return get_repository().transition_record(
            site_id=tenant,
            type_key=type_key,
            record_id=record_id,
            expected_version=payload.expected_version,
            actor_ref=f'user:{principal.user_id}',
            action=action,
            publish_at=payload.publish_at,
            timezone=payload.timezone,
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.delete('/types/{type_key}/records/{record_id}')
def delete_record(
    type_key: str,
    record_id: UUID,
    request: Request,
    expected_version: Annotated[int, Query(ge=1)],
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().soft_delete_record(
            site_id=tenant,
            type_key=type_key,
            record_id=record_id,
            expected_version=expected_version,
            actor_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/records/{record_id}')
def get_record(type_key: str, record_id: UUID, request: Request):
    _valid_type_key(type_key)
    _, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().get_record(site_id=tenant, type_key=type_key, record_id=record_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/records/{record_id}/versions')
def list_record_versions(type_key: str, record_id: UUID, request: Request):
    _valid_type_key(type_key)
    _, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().list_versions(
            site_id=tenant, type_key=type_key, record_id=record_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/records/{record_id}/versions/{version}/restore')
def restore_record(
    type_key: str,
    record_id: UUID,
    version: Annotated[int, Path(ge=1)],
    payload: RestoreRequest,
    request: Request,
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().restore_record(
            site_id=tenant,
            type_key=type_key,
            record_id=record_id,
            version=version,
            expected_version=payload.expected_version,
            actor_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/views')
def list_saved_views(type_key: str, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().list_views(
            site_id=tenant,
            type_key=type_key,
            owner_ref=f'user:{principal.user_id}',
            caller_role=getattr(request.state, 'content_workspace_role', None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/views', status_code=status.HTTP_201_CREATED)
def create_saved_view(type_key: str, payload: SavedViewCreate, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    if payload.visibility == 'private' and payload.shared_roles:
        raise HTTPException(status_code=422, detail='saved_view_roles_invalid')
    try:
        return get_repository().create_view(
            site_id=tenant,
            type_key=type_key,
            owner_ref=f'user:{principal.user_id}',
            payload=payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/views/{view_id}')
def get_saved_view(type_key: str, view_id: UUID, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().get_view(
            site_id=tenant,
            type_key=type_key,
            view_id=view_id,
            owner_ref=f'user:{principal.user_id}',
            caller_role=getattr(request.state, 'content_workspace_role', None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.patch('/types/{type_key}/views/{view_id}')
def update_saved_view(
    type_key: str,
    view_id: UUID,
    payload: SavedViewUpdate,
    request: Request,
    if_match: Annotated[str | None, Header(alias='If-Match')] = None,
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    expected = _expected_version(if_match, payload.expected_version)
    changes = payload.model_dump(exclude_none=True, exclude={'expected_version'})
    try:
        return get_repository().update_view(
            site_id=tenant,
            type_key=type_key,
            view_id=view_id,
            owner_ref=f'user:{principal.user_id}',
            expected_version=expected,
            payload=changes,
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.delete('/types/{type_key}/views/{view_id}')
def delete_saved_view(
    type_key: str,
    view_id: UUID,
    request: Request,
    expected_version: Annotated[int, Query(ge=1)],
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().delete_view(
            site_id=tenant,
            type_key=type_key,
            view_id=view_id,
            owner_ref=f'user:{principal.user_id}',
            expected_version=expected_version,
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 404, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/views/{view_id}/execute')
def execute_saved_view(type_key: str, view_id: UUID, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().execute_view(
            site_id=tenant,
            type_key=type_key,
            view_id=view_id,
            owner_ref=f'user:{principal.user_id}',
            caller_role=getattr(request.state, 'content_workspace_role', None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/assets/uploads', status_code=status.HTTP_201_CREATED)
def create_asset_upload(payload: AssetUploadCreate, request: Request):
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().create_asset_upload(
            site_id=tenant,
            owner_ref=f'user:{principal.user_id}',
            payload=payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/assets/{asset_id}')
def get_asset(asset_id: UUID, request: Request):
    principal, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().get_asset(
            site_id=tenant, asset_id=asset_id, requester_ref=f'user:{principal.user_id}'
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.put('/assets/{asset_id}/content')
async def complete_asset_upload(
    asset_id: UUID,
    request: Request,
    upload_grant: Annotated[str, Header(alias='Upload-Grant', min_length=32, max_length=4096)],
):
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    content_buffer = bytearray()
    async for chunk in request.stream():
        content_buffer.extend(chunk)
        if len(content_buffer) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail='content_limit_exceeded')
    content = bytes(content_buffer)
    try:
        return get_repository().complete_asset_upload(
            site_id=tenant,
            asset_id=asset_id,
            owner_ref=f'user:{principal.user_id}',
            upload_grant=upload_grant,
            content=content,
            artifact_store=get_artifact_store(),
        )
    except ArtifactIntegrityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        code = str(exc)
        status_code = 404 if code == 'content_not_found' else 422
        raise HTTPException(status_code=status_code, detail=code) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post(
    '/types/{type_key}/records/{record_id}/assets/{field_key}',
    status_code=status.HTTP_201_CREATED,
)
def bind_asset(
    type_key: str,
    record_id: UUID,
    field_key: str,
    payload: AssetBindingCreate,
    request: Request,
):
    _valid_type_key(type_key)
    _valid_type_key(field_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().bind_asset(
            site_id=tenant,
            type_key=type_key,
            record_id=record_id,
            field_key=field_key,
            expected_version=payload.expected_version,
            actor_ref=f'user:{principal.user_id}',
            payload=payload.model_dump(exclude={'expected_version'}),
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.delete('/types/{type_key}/records/{record_id}/assets/{field_key}')
def unbind_asset(
    type_key: str,
    record_id: UUID,
    field_key: str,
    asset_id: UUID,
    expected_version: Annotated[int, Query(ge=1)],
    request: Request,
):
    _valid_type_key(type_key)
    _valid_type_key(field_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().unbind_asset(
            site_id=tenant,
            type_key=type_key,
            record_id=record_id,
            field_key=field_key,
            asset_id=asset_id,
            expected_version=expected_version,
            actor_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/records/{record_id}/relationships')
def list_relationships(type_key: str, record_id: UUID, request: Request):
    _valid_type_key(type_key)
    _, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().list_relationships(
            site_id=tenant, type_key=type_key, record_id=record_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post(
    '/types/{type_key}/records/{record_id}/relationships',
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    type_key: str, record_id: UUID, payload: RelationshipCreate, request: Request
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().create_relationship(
            site_id=tenant,
            type_key=type_key,
            record_id=record_id,
            expected_version=payload.expected_version,
            actor_ref=f'user:{principal.user_id}',
            payload=payload.model_dump(exclude={'expected_version'}),
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.delete('/types/{type_key}/records/{record_id}/relationships/{relationship_id}')
def delete_relationship(
    type_key: str,
    record_id: UUID,
    relationship_id: UUID,
    expected_version: Annotated[int, Query(ge=1)],
    request: Request,
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().delete_relationship(
            site_id=tenant,
            type_key=type_key,
            record_id=record_id,
            relationship_id=relationship_id,
            expected_version=expected_version,
            actor_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_version_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/imports', status_code=status.HTTP_201_CREATED)
def create_import(
    type_key: str,
    payload: ImportCreate,
    request: Request,
    idempotency_key: Annotated[str, Header(alias='Idempotency-Key', min_length=8, max_length=128)],
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().create_import(
            site_id=tenant,
            type_key=type_key,
            requester_ref=f'user:{principal.user_id}',
            idempotency_key=idempotency_key,
            payload=payload.model_dump(),
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_idempotency_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/imports/{job_id}')
def get_import(type_key: str, job_id: UUID, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().get_import(
            site_id=tenant,
            type_key=type_key,
            job_id=job_id,
            requester_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.put('/types/{type_key}/imports/{job_id}/source')
async def complete_import_source(
    type_key: str,
    job_id: UUID,
    request: Request,
    upload_grant: Annotated[str, Header(alias='Upload-Grant', min_length=32, max_length=4096)],
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    content_buffer = bytearray()
    async for chunk in request.stream():
        content_buffer.extend(chunk)
        if len(content_buffer) > MAX_IMPORT_BYTES:
            raise HTTPException(status_code=413, detail='content_limit_exceeded')
    try:
        return get_repository().complete_import_source(
            site_id=tenant,
            type_key=type_key,
            job_id=job_id,
            requester_ref=f'user:{principal.user_id}',
            upload_grant=upload_grant,
            content=bytes(content_buffer),
            artifact_store=get_artifact_store(),
        )
    except ArtifactIntegrityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if code == 'content_not_found' else 422,
            detail=code,
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/imports/{job_id}/commit')
def commit_import(type_key: str, job_id: UUID, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().commit_import(
            site_id=tenant,
            type_key=type_key,
            job_id=job_id,
            requester_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_job_terminal' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/imports/{job_id}/cancel')
def cancel_import(type_key: str, job_id: UUID, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.write')
    try:
        return get_repository().cancel_import(
            site_id=tenant,
            type_key=type_key,
            job_id=job_id,
            requester_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/exports', status_code=status.HTTP_201_CREATED)
def create_export(
    type_key: str,
    payload: ExportCreate,
    request: Request,
    idempotency_key: Annotated[str, Header(alias='Idempotency-Key', min_length=8, max_length=128)],
):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().create_export(
            site_id=tenant,
            type_key=type_key,
            requester_ref=f'user:{principal.user_id}',
            idempotency_key=idempotency_key,
            payload=payload.model_dump(),
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=409 if code == 'content_idempotency_conflict' else 422, detail=code
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.get('/types/{type_key}/exports/{job_id}')
def get_export(type_key: str, job_id: UUID, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().get_export(
            site_id=tenant,
            type_key=type_key,
            job_id=job_id,
            requester_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/exports/{job_id}/download')
def create_export_download(type_key: str, job_id: UUID, request: Request):
    _valid_type_key(type_key)
    principal, tenant = _authorized_scope(request, 'content-workspace.read')
    try:
        return get_repository().create_export_download(
            site_id=tenant,
            type_key=type_key,
            job_id=job_id,
            requester_ref=f'user:{principal.user_id}',
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc
