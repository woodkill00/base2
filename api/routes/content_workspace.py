from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.middleware.tenant import require_tenant
from api.repositories.content_workspace import PostgresContentWorkspaceRepository
from api.security.request_auth import require_authenticated_principal


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


class RestoreRequest(ContractModel):
    expected_version: int = Field(ge=1)


TRANSITION_ACTIONS = {
    'submit_review',
    'return_draft',
    'schedule',
    'publish',
    'archive',
    'restore',
    'delete',
}


def get_repository() -> PostgresContentWorkspaceRepository:
    return PostgresContentWorkspaceRepository()


def _scope(request: Request):
    principal = require_authenticated_principal(request)
    tenant = require_tenant(request)
    return principal, tenant


def authorize(*, principal, site_id: str, permission: str) -> None:
    from api.repositories.identity_admin import require_permission

    try:
        require_permission(user_id=principal.user_id, tenant_id=site_id, permission=permission)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc


def _authorized_scope(request: Request, permission: str):
    principal, tenant = _scope(request)
    authorize(principal=principal, site_id=tenant, permission=permission)
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
    cursor: UUID | None = None,
):
    _, tenant = _authorized_scope(request, 'content.read')
    try:
        return get_repository().list_definitions(site_id=tenant, limit=limit, cursor=cursor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types', status_code=status.HTTP_201_CREATED)
def create_type(payload: DefinitionCreate, request: Request):
    principal, tenant = _authorized_scope(request, 'content.write')
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
    _, tenant = _authorized_scope(request, 'content.read')
    try:
        return get_repository().get_definition(site_id=tenant, type_key=type_key, version=version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='content_not_found') from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/versions/{version}/preview')
def preview_type(type_key: str, version: int, request: Request):
    _, tenant = _authorized_scope(request, 'content.write')
    try:
        return get_repository().preview_definition(
            site_id=tenant, type_key=type_key, version=version
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/versions/{version}/publish')
def publish_type(type_key: str, version: int, payload: DefinitionMutation, request: Request):
    principal, tenant = _authorized_scope(request, 'content.write')
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
def retire_type(type_key: str, version: int, payload: DefinitionMutation, request: Request):
    principal, tenant = _authorized_scope(request, 'content.write')
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
):
    _, tenant = _authorized_scope(request, 'content.read')
    if not IDENTIFIER.fullmatch(type_key):
        raise HTTPException(status_code=422, detail='content_identifier_invalid')
    try:
        return get_repository().list_records(
            site_id=tenant, type_key=type_key, limit=limit, cursor=cursor
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/records', status_code=status.HTTP_201_CREATED)
def create_record(type_key: str, payload: RecordCreate, request: Request):
    principal, tenant = _authorized_scope(request, 'content.write')
    if not IDENTIFIER.fullmatch(type_key):
        raise HTTPException(status_code=422, detail='content_identifier_invalid')
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
    principal, tenant = _authorized_scope(request, 'content.write')
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
    principal, tenant = _authorized_scope(request, 'content.write')
    if action not in TRANSITION_ACTIONS:
        raise HTTPException(status_code=422, detail='content_transition_invalid')
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
    principal, tenant = _authorized_scope(request, 'content.write')
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


@router.get('/types/{type_key}/records/{record_id}/versions')
def list_record_versions(type_key: str, record_id: UUID, request: Request):
    _, tenant = _authorized_scope(request, 'content.read')
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
    version: int,
    payload: RestoreRequest,
    request: Request,
):
    principal, tenant = _authorized_scope(request, 'content.write')
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
    principal, tenant = _authorized_scope(request, 'content.read')
    try:
        return get_repository().list_views(
            site_id=tenant, type_key=type_key, owner_ref=f'user:{principal.user_id}'
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='content_dependency_unavailable') from exc


@router.post('/types/{type_key}/views', status_code=status.HTTP_201_CREATED)
def create_saved_view(type_key: str, payload: SavedViewCreate, request: Request):
    principal, tenant = _authorized_scope(request, 'content.write')
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
