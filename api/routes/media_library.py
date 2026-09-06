"""Versioned, closed media-library API surface."""

from __future__ import annotations

import re
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.middleware.tenant import require_tenant
from api.repositories.content_workspace import PostgresContentWorkspaceRepository
from api.repositories.media_library import PostgresMediaLibraryRepository
from api.security.request_auth import require_authenticated_principal
from api.services.content_workspace_storage import ArtifactIntegrityError, configured_artifact_store
from api.services.media_library_policy import (
    DEFAULT_POLICY,
    FORMAT_RULES,
    delivery_headers,
    rule_for,
    validate_digest,
)
from api.settings import SITE_MANIFEST, settings


router = APIRouter(prefix="/media/v1", tags=["media-library"])
ASSET_STATES = {
    "pending", "uploaded", "inspecting", "accepted", "processing", "ready", "failed",
    "validated", "quarantined", "rejected", "archived", "deleted", "soft_deleted",
    "purge_planned",
}


def _camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.title() for part in rest)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=_camel)


class UploadCreate(ContractModel):
    filename: str = Field(min_length=1, max_length=200)
    media_type: Literal[
        "image/jpeg", "image/png", "image/webp", "application/pdf",
        "audio/mpeg", "audio/ogg", "video/mp4", "video/webm",
    ]
    byte_size: int = Field(ge=1, le=100 * 1024 * 1024)
    sha256: str

    @model_validator(mode="after")
    def policy_valid(self):
        rule = rule_for(display_name=self.filename, claimed_type=self.media_type)
        validate_digest(self.sha256)
        if self.byte_size > min(rule.maximum_bytes, int(DEFAULT_POLICY["maximumObjectBytes"])):
            raise ValueError("media_quota_object_exceeded")
        return self


class MetadataUpdate(ContractModel):
    locale: str = Field(default="en", pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", max_length=32)
    alt_text: str = Field(default="", max_length=500)
    decorative: bool = False
    caption: str = Field(default="", max_length=2_000)
    credit: str = Field(default="", max_length=500)
    license_code: str = Field(default="", pattern=r"^[A-Za-z0-9._-]{0,64}$")
    focal_x: float | None = Field(default=None, ge=0, le=1)
    focal_y: float | None = Field(default=None, ge=0, le=1)
    visibility: Literal["private", "authenticated", "public"] = "private"

    @field_validator("alt_text", "caption", "credit")
    @classmethod
    def no_controls(cls, value: str) -> str:
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value):
            raise ValueError("media_metadata_invalid")
        return value

    @model_validator(mode="after")
    def focal_pair(self):
        if (self.focal_x is None) != (self.focal_y is None):
            raise ValueError("media_focal_point_invalid")
        if self.decorative and self.alt_text:
            raise ValueError("media_decorative_alt_conflict")
        return self


def get_repository() -> PostgresMediaLibraryRepository:
    return PostgresMediaLibraryRepository()


def get_artifact_store():
    return configured_artifact_store(
        root=settings.CONTENT_WORKSPACE_STORAGE_ROOT,
        encoded_key=settings.CONTENT_WORKSPACE_STORAGE_KEY or "",
        max_bytes=runtime_policy()["maximumObjectBytes"],
    )


def authorize(*, principal, site_id: str, permission: str):
    from api.repositories.identity_admin import require_permission

    return require_permission(
        user_id=principal.user_id, tenant_id=site_id, permission=permission
    )


def runtime_policy() -> dict:
    configured = SITE_MANIFEST.get("media", {})
    allowed = configured.get("allowedTypes", DEFAULT_POLICY["allowedTypes"])
    maximum = configured.get("maxBytes", DEFAULT_POLICY["maximumObjectBytes"])
    if (
        not isinstance(allowed, list)
        or not allowed
        or len(allowed) != len(set(allowed))
        or any(item not in FORMAT_RULES for item in allowed)
        or not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or not 1 <= maximum <= 100 * 1024 * 1024
    ):
        raise RuntimeError("media_policy_invalid")
    return {"allowedTypes": allowed, "maximumObjectBytes": maximum}


def _authorized_scope(request: Request, permission: str):
    principal = require_authenticated_principal(request)
    tenant = require_tenant(request)
    try:
        authorize(principal=principal, site_id=tenant, permission=permission)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="media_not_found") from exc
    return principal, tenant


@router.get("/capabilities")
def capabilities(request: Request):
    _authorized_scope(request, "media.read")
    policy = runtime_policy()
    return {
        "schemaVersion": 1,
        "formats": [
            {"mediaType": rule.media_type, "extensions": list(rule.extensions), "delivery": rule.delivery}
            for rule in FORMAT_RULES.values()
            if rule.media_type in policy["allowedTypes"]
        ],
        "limits": {
            "maximumObjectBytes": policy["maximumObjectBytes"],
            "maximumBatchFiles": DEFAULT_POLICY["maximumBatchFiles"],
            "maximumBatchBytes": DEFAULT_POLICY["maximumBatchBytes"],
        },
    }


@router.get("/assets")
def list_assets(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    state: str | None = Query(default=None, max_length=24),
    media_type: str | None = Query(default=None, max_length=127),
    search: str | None = Query(default=None, min_length=1, max_length=100),
):
    _, tenant = _authorized_scope(request, "media.read")
    if state and state not in ASSET_STATES:
        raise HTTPException(status_code=422, detail="media_filter_invalid")
    if media_type and media_type not in FORMAT_RULES:
        raise HTTPException(status_code=422, detail="media_filter_invalid")
    try:
        return get_repository().list_assets(
            site_id=tenant, limit=limit, offset=offset, state=state,
            media_type=media_type, search=search,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="media_dependency_unavailable") from exc


@router.get("/assets/{asset_id}")
def get_asset(asset_id: UUID, request: Request):
    _, tenant = _authorized_scope(request, "media.read")
    try:
        return get_repository().get_asset(site_id=tenant, asset_id=asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="media_not_found") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="media_dependency_unavailable") from exc


@router.post("/uploads", status_code=201)
def create_upload(payload: UploadCreate, request: Request):
    principal, tenant = _authorized_scope(request, "media.upload")
    policy = runtime_policy()
    if (
        payload.media_type not in policy["allowedTypes"]
        or payload.byte_size > policy["maximumObjectBytes"]
    ):
        raise HTTPException(status_code=422, detail="media_policy_rejected")
    try:
        return PostgresContentWorkspaceRepository().create_asset_upload(
            site_id=tenant,
            owner_ref=f"user:{principal.user_id}",
            payload=payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="media_dependency_unavailable") from exc


@router.put("/assets/{asset_id}/content")
async def complete_upload(
    asset_id: UUID,
    request: Request,
    upload_grant: Annotated[str, Header(alias="Upload-Grant", min_length=32, max_length=4096)],
):
    principal, tenant = _authorized_scope(request, "media.upload")
    maximum = runtime_policy()["maximumObjectBytes"]
    buffer = bytearray()
    async for chunk in request.stream():
        buffer.extend(chunk)
        if len(buffer) > maximum:
            raise HTTPException(status_code=413, detail="media_quota_object_exceeded")
    try:
        return PostgresContentWorkspaceRepository().complete_asset_upload(
            site_id=tenant, asset_id=asset_id, owner_ref=f"user:{principal.user_id}",
            upload_grant=upload_grant, content=bytes(buffer), artifact_store=get_artifact_store(),
            maximum_bytes=maximum,
        )
    except (ValueError, ArtifactIntegrityError) as exc:
        code = str(exc)
        status_code = 404 if code == "content_not_found" else 422
        raise HTTPException(status_code=status_code, detail=code.replace("content_", "media_")) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="media_dependency_unavailable") from exc


@router.get("/assets/{asset_id}/content")
def read_content(
    asset_id: UUID,
    request: Request,
    download_grant: Annotated[str, Header(alias="Download-Grant", min_length=32, max_length=4096)],
):
    principal, tenant = _authorized_scope(request, "media.read")
    try:
        result = PostgresContentWorkspaceRepository().read_asset_content(
            site_id=tenant, asset_id=asset_id, requester_ref=f"user:{principal.user_id}",
            download_grant=download_grant, artifact_store=get_artifact_store(),
        )
        headers = delivery_headers(
            media_type=result["media_type"], inline_safe_derivative=result["media_type"].startswith("image/")
        )
        headers["X-Content-SHA256"] = result["sha256"]
        return Response(content=result["content"], media_type=result["media_type"], headers=headers)
    except (ValueError, ArtifactIntegrityError) as exc:
        code = str(exc)
        status_code = 404 if code == "content_not_found" else 422
        raise HTTPException(status_code=status_code, detail=code.replace("content_", "media_")) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="media_dependency_unavailable") from exc


@router.put("/assets/{asset_id}/metadata")
def update_metadata(
    asset_id: UUID,
    payload: MetadataUpdate,
    request: Request,
    if_match: Annotated[str, Header(alias="If-Match", min_length=1, max_length=32)],
):
    principal, tenant = _authorized_scope(request, "media.write")
    version = if_match.strip().strip('"')
    if not version.isdigit() or int(version) < 1:
        raise HTTPException(status_code=422, detail="media_expected_version_invalid")
    try:
        return get_repository().update_metadata(
            site_id=tenant, asset_id=asset_id, actor_ref=f"user:{principal.user_id}",
            expected_version=int(version), payload=payload.model_dump(by_alias=True),
        )
    except ValueError as exc:
        code = str(exc)
        status = 409 if code == "media_version_conflict" else 404 if code == "media_not_found" else 422
        raise HTTPException(status_code=status, detail=code) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="media_dependency_unavailable") from exc
