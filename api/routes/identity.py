from __future__ import annotations

import secrets
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.settings import settings
from api.middleware.tenant import require_tenant
from api.security.identity import (
    create_recovery_codes,
    generate_totp_secret,
    hash_sensitive_value,
    require_recent_reauthentication,
    verify_totp,
)
from api.security.request_auth import require_authenticated_principal
from api.security.secret_box import SecretBox, SecretBoxError

router = APIRouter(prefix="/identity", tags=["identity"])


class TotpConfirmRequest(BaseModel):
    authenticator_id: UUID
    code: str = Field(pattern=r'^\d{6}$')


class InvitationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    role: str


class CredentialRequest(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=list, max_length=20)


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class MemberRoleRequest(BaseModel):
    role: str
    expected_updated_at: datetime


class RecoveryRegenerateRequest(BaseModel):
    code: str = Field(pattern=r'^\d{6}$')


class OrganizationBootstrapRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


def _recent_principal(request: Request):
    principal = require_authenticated_principal(request)
    if not principal.recently_authenticated:
        raise HTTPException(status_code=401, detail='recent_reauthentication_required')
    try:
        require_recent_reauthentication(authenticated_at=principal.authenticated_at)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail='recent_reauthentication_required') from exc
    return principal


def _secret_box() -> SecretBox:
    key = str(settings.IDENTITY_ENCRYPTION_KEY or '').strip()
    if not key:
        raise HTTPException(status_code=503, detail='mfa_enrollment_unavailable')
    try:
        return SecretBox(key)
    except SecretBoxError as exc:
        raise HTTPException(status_code=503, detail='mfa_enrollment_unavailable') from exc


@router.get("/capabilities")
async def identity_capabilities():
    google_ready = bool(
        settings.GOOGLE_OAUTH_ENABLED
        and settings.GOOGLE_OAUTH_CLIENT_ID
        and settings.GOOGLE_OAUTH_CLIENT_SECRET
        and settings.GOOGLE_OAUTH_REDIRECT_URI
        and settings.OAUTH_STATE_SECRET
    )
    return {
        "account": {
            "password": {"enabled": True},
            "google_oauth": {"enabled": google_ready, "version": "v1"},
        },
        "mfa": {
            "totp": {"enabled": bool(settings.IDENTITY_ENCRYPTION_KEY), "version": "v1"},
            "recovery_codes": {"enabled": bool(settings.IDENTITY_ENCRYPTION_KEY), "version": "v1"},
            # The flag alone cannot claim an implementation. A versioned
            # WebAuthn ceremony remains a later activation.
            "webauthn": {"enabled": False, "version": "v1"},
        },
    }


@router.post('/mfa/totp/enroll')
async def enroll_totp(request: Request):
    from api.auth.repo import get_user_by_id, insert_audit_event
    from api.repositories.identity_admin import create_totp_authenticator

    principal = _recent_principal(request)
    user = get_user_by_id(principal.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='account_not_found')
    secret = generate_totp_secret()
    authenticator_id = create_totp_authenticator(
        user_id=principal.user_id, ciphertext=_secret_box().encrypt(secret)
    )
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.totp_enrollment_started',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'authenticator_id': str(authenticator_id)},
    )
    label = quote(user.email, safe='')
    issuer = quote(settings.SITE_NAME, safe='')
    return {
        'authenticator_id': str(authenticator_id),
        'otpauth_uri': f'otpauth://totp/{issuer}:{label}?secret={secret}&issuer={issuer}',
        'expires_in': 600,
    }


@router.post('/mfa/totp/confirm')
async def confirm_totp(payload: TotpConfirmRequest, request: Request):
    from api.auth.repo import insert_audit_event
    from api.repositories.identity_admin import pending_totp, activate_totp_with_recovery_codes

    principal = _recent_principal(request)
    ciphertext = pending_totp(
        user_id=principal.user_id, authenticator_id=payload.authenticator_id
    )
    if not ciphertext:
        raise HTTPException(status_code=404, detail='enrollment_not_found')
    secret = _secret_box().decrypt(ciphertext)
    if not verify_totp(secret, payload.code):
        raise HTTPException(status_code=400, detail='invalid_totp_code')
    recovery = create_recovery_codes(pepper=settings.TOKEN_PEPPER, count=8)
    if not activate_totp_with_recovery_codes(
        user_id=principal.user_id,
        authenticator_id=payload.authenticator_id,
        code_hashes=recovery.code_hashes,
    ):
        raise HTTPException(status_code=409, detail='enrollment_changed')
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.totp_enabled',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
    )
    return {'enabled': True, 'recovery_codes': list(recovery.plaintext_codes), 'shown_once': True}


@router.post('/mfa/recovery-codes/regenerate')
async def regenerate_recovery_codes(payload: RecoveryRegenerateRequest, request: Request):
    from api.auth.repo import insert_audit_event
    from api.repositories.identity_admin import active_totp, replace_recovery_codes

    principal = _recent_principal(request)
    authenticator = active_totp(user_id=principal.user_id)
    if authenticator is None:
        raise HTTPException(status_code=404, detail='mfa_not_enabled')
    secret = _secret_box().decrypt(authenticator['secret_ciphertext'])
    if not verify_totp(secret, payload.code):
        raise HTTPException(status_code=400, detail='invalid_totp_code')
    recovery = create_recovery_codes(pepper=settings.TOKEN_PEPPER, count=8)
    replace_recovery_codes(user_id=principal.user_id, code_hashes=recovery.code_hashes)
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.recovery_codes_regenerated',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
    )
    return {'recovery_codes': list(recovery.plaintext_codes), 'shown_once': True}


@router.post('/organization/bootstrap')
async def bootstrap_organization(payload: OrganizationBootstrapRequest, request: Request):
    from api.auth.repo import insert_audit_event
    from api.repositories.identity_admin import bootstrap_owner_organization

    if not settings.IDENTITY_ALLOW_FIRST_OWNER_BOOTSTRAP:
        raise HTTPException(status_code=404, detail='not_found')
    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    result = bootstrap_owner_organization(
        user_id=principal.user_id, tenant_id=tenant_id, name=payload.name
    )
    if result is None:
        raise HTTPException(status_code=409, detail='organization_already_initialized')
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.organization_bootstrapped',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'organization_id': str(result['organization_id']), 'tenant_id': tenant_id},
    )
    return {'organization_id': str(result['organization_id']), 'role': result['role']}


@router.post('/invitations/accept')
async def accept_invitation(payload: InvitationAcceptRequest, request: Request):
    from api.auth.repo import get_user_by_id, insert_audit_event
    from api.auth.tokens import hash_token
    from api.repositories.identity_admin import accept_invitation as accept

    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    user = get_user_by_id(principal.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='not_found')
    result = accept(
        token_hash=hash_token(payload.token),
        user_id=principal.user_id,
        user_email=user.email,
        tenant_id=tenant_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail='not_found')
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.invitation_accepted',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'organization_id': str(result['organization_id'])},
    )
    return {'organization_id': str(result['organization_id']), 'role': result['role']}


@router.get('/admin/overview')
async def get_admin_overview(request: Request):
    from api.repositories.identity_admin import admin_overview

    principal = require_authenticated_principal(request)
    tenant_id = require_tenant(request)
    try:
        return admin_overview(user_id=principal.user_id, tenant_id=tenant_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='not_found') from exc


@router.post('/admin/invitations')
async def invite_member(payload: InvitationRequest, request: Request):
    from api.auth.repo import insert_audit_event
    from api.auth.tokens import hash_token
    from api.repositories.identity_admin import require_permission, create_invitation

    if payload.role not in {'admin', 'editor', 'viewer'}:
        raise HTTPException(status_code=422, detail='invalid_role')
    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    try:
        member = require_permission(
            user_id=principal.user_id, tenant_id=tenant_id, permission='invitation.create'
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='not_found') from exc
    token = secrets.token_urlsafe(32)
    invitation_id = create_invitation(
        organization_id=member['organization_id'],
        actor_id=principal.user_id,
        email=payload.email,
        role=payload.role,
        token_hash=hash_token(token),
    )
    from api.services.email_service import queue_email

    invite_url = f"{str(settings.FRONTEND_URL or '').rstrip('/')}/accept-invitation?token={token}"
    queue_email(
        to_email=payload.email.strip().lower(),
        subject=f'Invitation to {settings.SITE_NAME}',
        body_text=f'Accept your invitation: {invite_url}',
        request_id=request.headers.get('x-request-id'),
        send_async=True,
    )
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.invitation_created',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'invitation_id': str(invitation_id), 'role': payload.role},
    )
    return {'id': str(invitation_id), 'status': 'queued_for_delivery'}


@router.delete('/admin/invitations/{invitation_id}')
async def revoke_member_invitation(invitation_id: UUID, request: Request):
    from api.auth.repo import insert_audit_event
    from api.repositories.identity_admin import require_permission, revoke_invitation

    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    try:
        member = require_permission(
            user_id=principal.user_id, tenant_id=tenant_id, permission='invitation.revoke'
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='not_found') from exc
    if not revoke_invitation(
        organization_id=member['organization_id'], invitation_id=invitation_id
    ):
        raise HTTPException(status_code=404, detail='not_found')
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.invitation_revoked',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'invitation_id': str(invitation_id)},
    )
    return {'revoked': True}


@router.patch('/admin/members/{member_id}/role')
async def change_member_role(member_id: UUID, payload: MemberRoleRequest, request: Request):
    from api.auth.repo import insert_audit_event
    from api.repositories.identity_admin import require_permission, update_member_role

    if payload.role not in {'owner', 'admin', 'editor', 'viewer'}:
        raise HTTPException(status_code=422, detail='invalid_role')
    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    try:
        actor = require_permission(
            user_id=principal.user_id, tenant_id=tenant_id, permission='member.manage'
        )
        changed = update_member_role(
            organization_id=actor['organization_id'],
            actor_id=principal.user_id,
            member_id=member_id,
            new_role=payload.role,
            expected_updated_at=payload.expected_updated_at,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='not_found') from exc
    except ValueError as exc:
        if str(exc) == 'last_owner':
            raise HTTPException(status_code=409, detail='last_owner_required') from exc
        raise
    if not changed:
        raise HTTPException(status_code=409, detail='membership_changed')
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.member_role_changed',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'member_id': str(member_id), 'role': payload.role},
    )
    return {'updated': True, 'role': payload.role}


@router.post('/admin/credentials')
async def create_credential(payload: CredentialRequest, request: Request):
    from api.auth.repo import insert_audit_event
    from api.repositories.identity_admin import require_permission, create_api_credential

    allowed_scopes = {'content.read', 'content.write'}
    scopes = sorted(set(payload.scopes))
    if not scopes or not set(scopes) <= allowed_scopes:
        raise HTTPException(status_code=422, detail='invalid_scopes')
    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    try:
        member = require_permission(
            user_id=principal.user_id, tenant_id=tenant_id, permission='credential.create'
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='not_found') from exc
    raw_secret = secrets.token_urlsafe(32)
    prefix = f'b2_{secrets.token_hex(4)}'
    credential_id = create_api_credential(
        organization_id=member['organization_id'],
        actor_id=principal.user_id,
        label=payload.label,
        prefix=prefix,
        secret_hash=hash_sensitive_value(raw_secret, pepper=settings.TOKEN_PEPPER),
        scopes=scopes,
    )
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.credential_created',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'credential_id': str(credential_id), 'prefix': prefix, 'scopes': scopes},
    )
    return {
        'id': str(credential_id),
        'prefix': prefix,
        'secret': f'{prefix}.{raw_secret}',
        'shown_once': True,
        'scopes': scopes,
    }


@router.delete('/admin/credentials/{credential_id}')
async def revoke_credential(credential_id: UUID, request: Request):
    from api.auth.repo import insert_audit_event
    from api.repositories.identity_admin import require_permission, revoke_api_credential

    principal = _recent_principal(request)
    tenant_id = require_tenant(request)
    try:
        member = require_permission(
            user_id=principal.user_id, tenant_id=tenant_id, permission='credential.revoke'
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail='not_found') from exc
    if not revoke_api_credential(
        organization_id=member['organization_id'], credential_id=credential_id
    ):
        raise HTTPException(status_code=404, detail='not_found')
    insert_audit_event(
        user_id=principal.user_id,
        action='identity.credential_revoked',
        ip='',
        user_agent=request.headers.get('user-agent', ''),
        metadata={'credential_id': str(credential_id)},
    )
    return {'revoked': True}
