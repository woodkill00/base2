import socket

import pytest

from api.services.commercial_packs import (
    CommercePack, MarketplacePack, MembershipPack, PackPolicyError, PackSettings,
)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError('commercial packs attempted a live network call')
    monkeypatch.setattr(socket, 'create_connection', blocked)
    monkeypatch.setattr(socket.socket, 'connect', blocked)


@pytest.mark.parametrize('pack', [MembershipPack, CommercePack, MarketplacePack])
def test_pack_is_disabled_by_default(pack):
    with pytest.raises(PackPolicyError, match='disabled'):
        pack(PackSettings())


def test_membership_local_fake_is_deterministic():
    pack = MembershipPack(PackSettings(enabled=True, provider='local_fake'))
    pack.add_plan(plan_id='monthly-plan', amount_minor=900, currency='USD')
    first = pack.subscribe(tenant_id='site-a', member_id='member-a', plan_id='monthly-plan', replay_key='one')
    second = pack.subscribe(tenant_id='site-a', member_id='member-a', plan_id='monthly-plan', replay_key='one')
    assert first == second and first['provider'] == 'local_fake'


def test_commerce_catalog_rejects_unknown_and_charges_known_product():
    pack = CommercePack(PackSettings(enabled=True, provider='local_fake'))
    with pytest.raises(PackPolicyError, match='not_found'):
        pack.checkout(tenant_id='site-a', sku='missing', replay_key='one')
    pack.add_product(sku='safe-product', amount_minor=1250, currency='EUR')
    assert pack.checkout(tenant_id='site-a', sku='safe-product', replay_key='one')['status'] == 'authorized'


def test_marketplace_requires_moderation_and_blocks_self_purchase():
    pack = MarketplacePack(PackSettings(enabled=True, provider='local_fake'))
    pack.add_listing(listing_id='listing-one', seller_id='seller-a', amount_minor=700, currency='USD')
    with pytest.raises(PackPolicyError, match='not_available'):
        pack.purchase(tenant_id='site-a', listing_id='listing-one', buyer_id='buyer-a', replay_key='one')
    pack.publish('listing-one')
    with pytest.raises(PackPolicyError, match='self_purchase'):
        pack.purchase(tenant_id='site-a', listing_id='listing-one', buyer_id='seller-a', replay_key='one')
    assert pack.purchase(tenant_id='site-a', listing_id='listing-one', buyer_id='buyer-a', replay_key='one')['provider'] == 'local_fake'


def test_commercial_input_and_provider_boundaries_fail_closed():
    with pytest.raises(PackPolicyError, match='provider_not_allowlisted'):
        CommercePack(PackSettings(enabled=True, provider='live'))
    membership = MembershipPack(PackSettings(enabled=True, provider='local_fake'))
    with pytest.raises(PackPolicyError, match='plan_id'):
        membership.add_plan(plan_id='../bad', amount_minor=1, currency='USD')
    with pytest.raises(PackPolicyError, match='amount'):
        membership.add_plan(plan_id='valid-plan', amount_minor=0, currency='USD')
    with pytest.raises(PackPolicyError, match='not_found'):
        membership.subscribe(tenant_id='site-a', member_id='m', plan_id='missing', replay_key='r')
    commerce = CommercePack(PackSettings(enabled=True, provider='local_fake'))
    with pytest.raises(PackPolicyError, match='sku'):
        commerce.add_product(sku='?', amount_minor=1, currency='USD')
    with pytest.raises(PackPolicyError, match='amount'):
        commerce.add_product(sku='valid-sku', amount_minor=0, currency='USD')
    marketplace = MarketplacePack(PackSettings(enabled=True, provider='local_fake'))
    with pytest.raises(PackPolicyError, match='listing'):
        marketplace.add_listing(listing_id='valid-listing', seller_id='', amount_minor=1, currency='USD')
    with pytest.raises(PackPolicyError, match='not_found'):
        marketplace.publish('missing')
