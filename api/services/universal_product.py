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
SEARCH_DOCUMENT_FIELDS = {
    'id', 'tenantId', 'kind', 'title', 'body', 'urlPath', 'permissions', 'facets',
    'sourceUpdatedAt', 'authorizationEpoch', 'deleted', 'indexed',
}


class ProductContractError(ValueError):
    pass


def validate_search_manifest(value: Any) -> dict[str, Any]:
    required = {
        'schemaVersion', 'enabledByDefault', 'documentFields', 'filters', 'facets',
        'ranking', 'maximumResults', 'freshnessSeconds', 'deletionSeconds',
    }
    if not isinstance(value, dict) or set(value) != required or value['schemaVersion'] != 1:
        raise ProductContractError('search:manifest_invalid')
    if set(value['documentFields']) != SEARCH_DOCUMENT_FIELDS:
        raise ProductContractError('search:manifest_invalid')
    if value['enabledByDefault'] is not False or value['ranking'] != [
        'permission', 'exact-title', 'term-frequency', 'freshness', 'stable-id'
    ]:
        raise ProductContractError('search:manifest_invalid')
    if not 1 <= value['maximumResults'] <= 100 or not 1 <= value['freshnessSeconds'] <= 3600:
        raise ProductContractError('search:manifest_invalid')
    if not 1 <= value['deletionSeconds'] <= value['freshnessSeconds']:
        raise ProductContractError('search:manifest_invalid')
    if any(not re.fullmatch(r'[a-z][a-zA-Z0-9]*', item) for item in value['filters'] + value['facets']):
        raise ProductContractError('search:manifest_invalid')
    return json.loads(json.dumps(value, sort_keys=True))


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


def index_action(
    document: dict[str, Any], *, tenant_id: str, authorization_epoch: int,
    provider_available: bool,
) -> dict[str, Any]:
    if document.get('tenantId') != tenant_id or authorization_epoch < 1:
        raise ProductContractError('search:index_scope_invalid')
    if not provider_available:
        return {
            'state': 'retry', 'operation': 'none', 'errorCode': 'search.provider_unavailable',
            'operationsSignal': True,
        }
    if document.get('deleted'):
        operation = 'delete'
    elif document.get('authorizationEpoch') != authorization_epoch:
        operation = 'replace-permissions'
    else:
        operation = 'upsert'
    return {
        'state': 'ready', 'operation': operation, 'authorizationEpoch': authorization_epoch,
        'operationsSignal': False,
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
