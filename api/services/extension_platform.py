"""Safe visual composition, integration, and optional commerce contracts."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

COMPONENTS = {'section', 'heading', 'text', 'image', 'link', 'button', 'grid', 'card', 'form'}
ARCHETYPES = {
    'business',
    'portfolio',
    'documentation',
    'publication',
    'community',
    'directory',
    'event',
    'booking',
    'catalog',
    'marketplace',
    'subscription',
    'support',
    'nonprofit',
}
COMMERCE_STATES = {
    'order': {
        'pending': {'confirmed', 'cancelled'},
        'confirmed': {'refunded'},
        'refunded': set(),
        'cancelled': set(),
    },
    'subscription': {
        'trial': {'active', 'cancelled'},
        'active': {'past-due', 'cancelled'},
        'past-due': {'active', 'cancelled'},
        'cancelled': set(),
    },
}


class ExtensionContractError(ValueError):
    pass


def compose_page(tree: dict[str, Any]) -> dict[str, Any]:
    count = 0

    def visit(node: Any, depth: int) -> dict[str, Any]:
        nonlocal count
        if not isinstance(node, dict) or set(node) != {'component', 'props', 'children'}:
            raise ExtensionContractError('builder:node_invalid')
        if node['component'] not in COMPONENTS or depth > 4:
            raise ExtensionContractError('builder:component_forbidden')
        if not isinstance(node['props'], dict) or not isinstance(node['children'], list):
            raise ExtensionContractError('builder:shape_invalid')
        encoded = json.dumps(node['props']).casefold()
        if any(
            marker in encoded
            for marker in ('<script', 'javascript:', 'onerror', 'onclick', 'style=')
        ):
            raise ExtensionContractError('builder:executable_content_forbidden')
        count += 1
        if count > 64:
            raise ExtensionContractError('builder:node_limit')
        return {
            'component': node['component'],
            'props': json.loads(json.dumps(node['props'], sort_keys=True)),
            'children': [visit(child, depth + 1) for child in node['children']],
        }

    result = visit(tree, 1)
    return {'schemaVersion': 1, 'tree': result, 'nodeCount': count, 'executableMarkup': False}


def theme_upgrade(
    *, current_version: int, target_version: int, tokens: dict[str, Any], required: set[str]
) -> dict[str, Any]:
    if target_version != current_version + 1 or set(tokens) != required:
        raise ExtensionContractError('theme:incompatible')
    if any(value in {'transparent', '', None} for value in tokens.values()):
        raise ExtensionContractError('theme:token_invalid')
    digest = hashlib.sha256(
        json.dumps(tokens, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    return {
        'fromVersion': current_version,
        'toVersion': target_version,
        'tokenDigest': digest,
        'previewRequired': True,
        'accessibilityValidationRequired': True,
        'rollbackVersion': current_version,
    }


def archetype_contract(
    name: str, *, modules: list[str], provider_cost_ceiling: float
) -> dict[str, Any]:
    if name not in ARCHETYPES or not modules or not 0 <= provider_cost_ceiling <= 1000:
        raise ExtensionContractError('archetype:invalid')
    return {
        'name': name,
        'modules': sorted(set(modules)),
        'routesDeclared': True,
        'rolesDeclared': True,
        'seedDataSynthetic': True,
        'journeysDeclared': True,
        'visualProfilesDeclared': True,
        'capacityAssumptionsDeclared': True,
        'providerCostCeiling': provider_cost_ceiling,
    }


def integration_grant(
    *, tenant_id: str, scopes: set[str], expires_at: datetime, now: datetime, key_material: bytes
) -> dict[str, Any]:
    if (
        not re.fullmatch(r'[a-z][a-z0-9-]{2,62}', tenant_id or '')
        or not scopes
        or any(not re.fullmatch(r'[a-z][a-z0-9:.-]{2,63}', item) for item in scopes)
        or now.tzinfo is None
        or expires_at.tzinfo is None
        or not now < expires_at <= now + timedelta(days=90)
        or len(key_material) < 32
    ):
        raise ExtensionContractError('integration:grant_invalid')
    return {
        'tenantId': tenant_id,
        'scopes': sorted(scopes),
        'expiresAt': expires_at.astimezone(UTC).isoformat(),
        'keyFingerprint': hashlib.sha256(key_material).hexdigest()[:16],
        'rotationRequired': True,
        'revocable': True,
        'secretValueStored': False,
    }


def verify_webhook(
    *,
    body: bytes,
    signature: str,
    timestamp: datetime,
    now: datetime,
    key: bytes,
    delivery_id: str,
    seen: set[str],
) -> dict[str, Any]:
    if (
        now.tzinfo is None
        or timestamp.tzinfo is None
        or abs((now - timestamp).total_seconds()) > 300
    ):
        raise ExtensionContractError('webhook:expired')
    if delivery_id in seen:
        return {'status': 'duplicate-noop', 'sideEffects': 0}
    signed = timestamp.astimezone(UTC).isoformat().encode() + b'.' + body
    expected = hmac.new(key, signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ExtensionContractError('webhook:signature_invalid')
    seen.add(delivery_id)
    return {'status': 'accepted', 'sideEffects': 1, 'deliveryId': delivery_id}


def api_contract(
    *, version: int, sunset_at: datetime | None, consumers_observed: int
) -> dict[str, Any]:
    if version < 1 or consumers_observed < 0 or (sunset_at and sunset_at.tzinfo is None):
        raise ExtensionContractError('api:contract_invalid')
    return {
        'version': version,
        'compatibility': 'additive-within-major',
        'sunsetAt': sunset_at.astimezone(UTC).isoformat() if sunset_at else None,
        'consumerContractsRequired': True,
        'consumersObserved': consumers_observed,
        'productionSecretsAllowed': False,
    }


def commerce_transition(
    *, kind: str, state: str, target: str, provider: str, idempotency_key: str
) -> dict[str, Any]:
    if provider != 'fake' or kind not in COMMERCE_STATES:
        raise ExtensionContractError('commerce:provider_disabled')
    if target not in COMMERCE_STATES[kind].get(state, set()):
        raise ExtensionContractError('commerce:transition_invalid')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', idempotency_key or ''):
        raise ExtensionContractError('commerce:idempotency_invalid')
    return {
        'kind': kind,
        'from': state,
        'to': target,
        'provider': 'fake',
        'idempotencyKey': idempotency_key,
        'prohibitedPaymentDataStored': False,
        'reconciliationRequired': True,
    }
