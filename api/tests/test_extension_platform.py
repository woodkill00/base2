import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import pytest

from api.services.extension_platform import (
    ARCHETYPES,
    ExtensionContractError,
    api_contract,
    archetype_contract,
    commerce_transition,
    compose_page,
    integration_grant,
    theme_upgrade,
    verify_webhook,
)

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)
KEY = b's' * 32


def test_builder_is_closed_bounded_and_deterministic():
    tree = {
        'component': 'section',
        'props': {'label': 'Intro'},
        'children': [{'component': 'heading', 'props': {'text': 'Hello'}, 'children': []}],
    }
    assert compose_page(tree) == compose_page(tree)
    assert compose_page(tree)['nodeCount'] == 2
    hostile = {'component': 'text', 'props': {'value': '<script>alert(1)</script>'}, 'children': []}
    with pytest.raises(ExtensionContractError, match='executable'):
        compose_page(hostile)


def test_theme_upgrade_and_every_archetype_have_closed_contracts():
    upgrade = theme_upgrade(
        current_version=1,
        target_version=2,
        tokens={'color': '#000', 'space': 8, 'motion': 0},
        required={'color', 'space', 'motion'},
    )
    assert upgrade['previewRequired'] and upgrade['rollbackVersion'] == 1
    contracts = [
        archetype_contract(name, modules=['content'], provider_cost_ceiling=25)
        for name in ARCHETYPES
    ]
    assert len(contracts) == 13 and all(item['seedDataSynthetic'] for item in contracts)


def test_integration_grants_are_scoped_expiring_and_value_free():
    grant = integration_grant(
        tenant_id='tenant-one',
        scopes={'content:read'},
        expires_at=NOW + timedelta(days=30),
        now=NOW,
        key_material=KEY,
    )
    assert grant['secretValueStored'] is False and grant['scopes'] == ['content:read']
    with pytest.raises(ExtensionContractError):
        integration_grant(
            tenant_id='tenant-one',
            scopes={'*'},
            expires_at=NOW + timedelta(days=30),
            now=NOW,
            key_material=KEY,
        )


def test_webhooks_are_signed_fresh_and_replay_safe():
    body = b'{"event":"content.updated"}'
    signed = NOW.isoformat().encode() + b'.' + body
    signature = hmac.new(KEY, signed, hashlib.sha256).hexdigest()
    seen = set()
    assert (
        verify_webhook(
            body=body,
            signature=signature,
            timestamp=NOW,
            now=NOW,
            key=KEY,
            delivery_id='delivery-0001',
            seen=seen,
        )['sideEffects']
        == 1
    )
    assert (
        verify_webhook(
            body=body,
            signature=signature,
            timestamp=NOW,
            now=NOW,
            key=KEY,
            delivery_id='delivery-0001',
            seen=seen,
        )['status']
        == 'duplicate-noop'
    )
    with pytest.raises(ExtensionContractError, match='expired'):
        verify_webhook(
            body=body,
            signature=signature,
            timestamp=NOW,
            now=NOW + timedelta(minutes=6),
            key=KEY,
            delivery_id='delivery-0002',
            seen=seen,
        )


def test_public_api_and_fake_commerce_are_versioned_and_safe():
    contract = api_contract(version=2, sunset_at=NOW + timedelta(days=90), consumers_observed=3)
    assert contract['consumerContractsRequired'] and not contract['productionSecretsAllowed']
    order = commerce_transition(
        kind='order',
        state='pending',
        target='confirmed',
        provider='fake',
        idempotency_key='order-request-0001',
    )
    assert order['reconciliationRequired'] and not order['prohibitedPaymentDataStored']
    with pytest.raises(ExtensionContractError, match='provider_disabled'):
        commerce_transition(
            kind='order',
            state='pending',
            target='confirmed',
            provider='live',
            idempotency_key='order-request-0001',
        )
