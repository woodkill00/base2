from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from api.providers.payments import LocalFakePaymentProvider, PaymentActivation, PaymentBoundaryError


class PackPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class PackSettings:
    enabled: bool = False
    provider: str = 'none'

    def payment_provider(self) -> LocalFakePaymentProvider:
        if not self.enabled:
            raise PackPolicyError('pack:disabled')
        if self.provider != 'local_fake':
            raise PackPolicyError('pack:provider_not_allowlisted')
        return LocalFakePaymentProvider(
            PaymentActivation(enabled=True, mode='local_fake', provider='local_fake')
        )


def _slug(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,62}', value):
        raise PackPolicyError(f'{field}:invalid')
    return value


class MembershipPack:
    def __init__(self, settings: PackSettings):
        self.provider = settings.payment_provider()
        self.plans: dict[str, dict[str, Any]] = {}

    def add_plan(self, *, plan_id: str, amount_minor: int, currency: str):
        plan_id = _slug(plan_id, 'plan_id')
        if amount_minor < 1:
            raise PackPolicyError('amount:invalid')
        self.plans[plan_id] = {'amountMinor': amount_minor, 'currency': currency}

    def subscribe(self, *, tenant_id: str, member_id: str, plan_id: str, replay_key: str):
        plan = self.plans.get(plan_id)
        if plan is None:
            raise PackPolicyError('plan:not_found')
        receipt = self.provider.charge(
            tenant_id=tenant_id,
            amount_minor=plan['amountMinor'],
            currency=plan['currency'],
            replay_key=f'{member_id}:{plan_id}:{replay_key}',
        )
        return {'memberId': member_id, 'planId': plan_id, **receipt}


class CommercePack:
    def __init__(self, settings: PackSettings):
        self.provider = settings.payment_provider()
        self.catalog: dict[str, dict[str, Any]] = {}

    def add_product(self, *, sku: str, amount_minor: int, currency: str):
        sku = _slug(sku, 'sku')
        if amount_minor < 1:
            raise PackPolicyError('amount:invalid')
        self.catalog[sku] = {'amountMinor': amount_minor, 'currency': currency}

    def checkout(self, *, tenant_id: str, sku: str, replay_key: str):
        product = self.catalog.get(sku)
        if product is None:
            raise PackPolicyError('product:not_found')
        return self.provider.charge(
            tenant_id=tenant_id,
            replay_key=replay_key,
            amount_minor=product['amountMinor'],
            currency=product['currency'],
        )


class MarketplacePack:
    def __init__(self, settings: PackSettings):
        self.provider = settings.payment_provider()
        self.listings: dict[str, dict[str, Any]] = {}

    def add_listing(self, *, listing_id: str, seller_id: str, amount_minor: int, currency: str):
        listing_id = _slug(listing_id, 'listing_id')
        if not seller_id or amount_minor < 1:
            raise PackPolicyError('listing:invalid')
        self.listings[listing_id] = {
            'sellerId': seller_id, 'amountMinor': amount_minor, 'currency': currency,
            'moderationStatus': 'pending',
        }

    def publish(self, listing_id: str):
        listing = self.listings.get(listing_id)
        if listing is None:
            raise PackPolicyError('listing:not_found')
        listing['moderationStatus'] = 'published'

    def purchase(self, *, tenant_id: str, listing_id: str, buyer_id: str, replay_key: str):
        listing = self.listings.get(listing_id)
        if listing is None or listing['moderationStatus'] != 'published':
            raise PackPolicyError('listing:not_available')
        if buyer_id == listing['sellerId']:
            raise PackPolicyError('listing:self_purchase')
        try:
            return self.provider.charge(
                tenant_id=tenant_id,
                amount_minor=listing['amountMinor'],
                currency=listing['currency'],
                replay_key=replay_key,
            )
        except PaymentBoundaryError as exc:
            raise PackPolicyError(str(exc)) from exc
