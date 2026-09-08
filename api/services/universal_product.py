"""Closed, tenant-safe contracts for optional universal product capabilities."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

TENANT = re.compile(r'^[a-z][a-z0-9-]{2,62}$')
SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
EDITORIAL = {'draft', 'review', 'scheduled', 'published', 'archived'}


class ProductContractError(ValueError):
    pass


def search_results(
    documents: list[dict[str, Any]],
    *,
    tenant_id: str,
    actor_permissions: set[str],
    query: str,
    cursor: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    if not TENANT.fullmatch(tenant_id or '') or not query.strip() or not 1 <= limit <= 50:
        raise ProductContractError('search:request_invalid')
    if cursor < 0:
        raise ProductContractError('search:cursor_invalid')
    terms = set(query.casefold().split())
    matches = []
    for item in documents:
        if item.get('tenantId') != tenant_id or item.get('deleted') or not item.get('indexed'):
            continue
        required = set(item.get('permissions', []))
        if not required.issubset(actor_permissions):
            continue
        haystack = f"{item.get('title', '')} {item.get('body', '')}".casefold()
        score = sum(term in haystack for term in terms)
        if score:
            matches.append((score, item['id'], item))
    matches.sort(key=lambda row: (-row[0], row[1]))
    page = [json.loads(json.dumps(row[2])) for row in matches[cursor : cursor + limit]]
    next_cursor = cursor + limit if cursor + limit < len(matches) else None
    return {
        'items': page,
        'nextCursor': next_cursor,
        'tenantId': tenant_id,
        'authorizationFiltered': True,
    }


def editorial_transition(
    *, state: str, target: str, revision: int, expected_revision: int, approved: bool = False
) -> dict[str, Any]:
    allowed = {
        'draft': {'review', 'archived'},
        'review': {'draft', 'scheduled', 'published'},
        'scheduled': {'draft', 'published'},
        'published': {'draft', 'archived'},
        'archived': {'draft'},
    }
    if state not in EDITORIAL or target not in allowed[state]:
        raise ProductContractError('editorial:transition_invalid')
    if revision != expected_revision:
        raise ProductContractError('editorial:revision_conflict')
    if target in {'scheduled', 'published'} and not approved:
        raise ProductContractError('editorial:approval_required')
    return {
        'from': state,
        'to': target,
        'revision': revision + 1,
        'rollbackState': state,
        'conflictChecked': True,
    }


def preview_token(
    *,
    tenant_id: str,
    content_id: str,
    permission: str,
    expires_at: datetime,
    now: datetime,
    key: bytes,
) -> str:
    if (
        not TENANT.fullmatch(tenant_id or '')
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{2,127}', content_id or '')
        or not re.fullmatch(r'[a-z][a-z0-9:.-]{2,63}', permission or '')
        or expires_at.tzinfo is None
        or now.tzinfo is None
        or not now < expires_at <= now + timedelta(hours=1)
        or len(key) < 32
    ):
        raise ProductContractError('preview:invalid')
    body = json.dumps(
        {
            'tenantId': tenant_id,
            'contentId': content_id,
            'permission': permission,
            'expiresAt': expires_at.astimezone(UTC).isoformat(),
        },
        sort_keys=True,
        separators=(',', ':'),
    )
    return f'{body}.{hmac.new(key, body.encode(), hashlib.sha256).hexdigest()}'


def verify_preview(
    token: str, *, tenant_id: str, permission: str, now: datetime, key: bytes
) -> dict[str, Any]:
    if len(key) < 32:
        raise ProductContractError('preview:invalid')
    try:
        body, signature = token.rsplit('.', 1)
        value = json.loads(body)
        expected = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
        expiry = datetime.fromisoformat(value['expiresAt'])
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ProductContractError('preview:invalid') from exc
    if (
        not hmac.compare_digest(signature, expected)
        or value['tenantId'] != tenant_id
        or value['permission'] != permission
        or now.tzinfo is None
        or expiry <= now
    ):
        raise ProductContractError('preview:denied')
    return {**value, 'cacheControl': 'private, no-store', 'authorized': True}


def media_deletion(*, references: list[str], force: bool, approved: bool) -> dict[str, Any]:
    if force and not approved:
        raise ProductContractError('media:approval_required')
    if references and not force:
        return {
            'status': 'blocked-referenced',
            'references': sorted(set(references)),
            'deleted': False,
        }
    return {'status': 'deleted', 'references': [], 'deleted': True}


def public_contract(*, locale: str, canonical_path: str, consent: str) -> dict[str, Any]:
    if not re.fullmatch(r'[a-z]{2}(?:-[A-Z]{2})?', locale or ''):
        raise ProductContractError('public:locale_invalid')
    if (
        not canonical_path.startswith('/')
        or '//' in canonical_path
        or consent
        not in {
            'necessary-only',
            'granted',
            'denied',
        }
    ):
        raise ProductContractError('public:contract_invalid')
    return {
        'locale': locale,
        'canonicalPath': canonical_path,
        'metadata': ['canonical', 'description', 'open-graph', 'structured-data'],
        'discovery': ['sitemap', 'robots'],
        'navigation': ['header', 'breadcrumb', 'footer', 'skip-link'],
        'states': ['loading', 'empty', 'degraded', 'denied', 'error'],
        'consent': consent,
        'analyticsEnabled': consent == 'granted',
        'printAndShare': True,
    }


def disabled_capability(name: str) -> dict[str, Any]:
    if name not in {'search', 'builder', 'commerce', 'integrations'}:
        raise ProductContractError('capability:unknown')
    return {
        'name': name,
        'enabled': False,
        'routes': [],
        'navigation': [],
        'jobs': [],
        'schedules': [],
        'allocations': [],
        'credentials': [],
        'authority': [],
    }
