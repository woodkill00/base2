from datetime import UTC, datetime, timedelta

import pytest

from api.services.universal_product import (
    ProductContractError,
    disabled_capability,
    editorial_transition,
    media_deletion,
    preview_token,
    public_contract,
    search_results,
    verify_preview,
)

NOW = datetime(2026, 9, 8, tzinfo=UTC)
KEY = b'k' * 32


def test_search_is_bounded_ranked_permission_and_tenant_aware():
    documents = [
        {
            'id': 'a',
            'tenantId': 'tenant-one',
            'title': 'Blue sky',
            'body': 'blue',
            'permissions': ['read'],
            'indexed': True,
        },
        {
            'id': 'b',
            'tenantId': 'tenant-one',
            'title': 'Blue',
            'body': '',
            'permissions': ['admin'],
            'indexed': True,
        },
        {
            'id': 'c',
            'tenantId': 'tenant-two',
            'title': 'Blue blue',
            'body': '',
            'permissions': ['read'],
            'indexed': True,
        },
        {
            'id': 'd',
            'tenantId': 'tenant-one',
            'title': 'Blue',
            'body': '',
            'permissions': ['read'],
            'indexed': True,
            'deleted': True,
        },
    ]
    result = search_results(
        documents, tenant_id='tenant-one', actor_permissions={'read'}, query='blue', limit=1
    )
    assert [item['id'] for item in result['items']] == ['a']
    assert result['authorizationFiltered'] and result['nextCursor'] is None
    with pytest.raises(ProductContractError):
        search_results(
            documents, tenant_id='tenant-one', actor_permissions={'read'}, query='blue', limit=51
        )


def test_editorial_conflict_review_and_rollback_are_explicit():
    with pytest.raises(ProductContractError, match='approval'):
        editorial_transition(state='review', target='published', revision=2, expected_revision=2)
    published = editorial_transition(
        state='review', target='published', revision=2, expected_revision=2, approved=True
    )
    assert published == {
        'from': 'review',
        'to': 'published',
        'revision': 3,
        'rollbackState': 'review',
        'conflictChecked': True,
    }
    with pytest.raises(ProductContractError, match='conflict'):
        editorial_transition(state='draft', target='review', revision=3, expected_revision=2)


def test_preview_is_expiring_permission_tenant_and_cache_safe():
    token = preview_token(
        tenant_id='tenant-one',
        content_id='post-1',
        permission='content.preview',
        expires_at=NOW + timedelta(minutes=5),
        key=KEY,
    )
    result = verify_preview(
        token, tenant_id='tenant-one', permission='content.preview', now=NOW, key=KEY
    )
    assert result['cacheControl'] == 'private, no-store'
    for tenant, permission, now in (
        ('tenant-two', 'content.preview', NOW),
        ('tenant-one', 'content.publish', NOW),
        ('tenant-one', 'content.preview', NOW + timedelta(minutes=6)),
    ):
        with pytest.raises(ProductContractError):
            verify_preview(token, tenant_id=tenant, permission=permission, now=now, key=KEY)
    with pytest.raises(ProductContractError, match='invalid'):
        preview_token(
            tenant_id='tenant-one',
            content_id='',
            permission='content.preview',
            expires_at=NOW + timedelta(minutes=5),
            key=KEY,
        )


def test_reference_aware_media_and_public_privacy_contracts():
    blocked = media_deletion(references=['page-2', 'page-1'], force=False, approved=False)
    assert blocked['references'] == ['page-1', 'page-2'] and not blocked['deleted']
    with pytest.raises(ProductContractError, match='approval'):
        media_deletion(references=['page-1'], force=True, approved=False)
    assert media_deletion(references=['page-1'], force=True, approved=True)['deleted']
    necessary = public_contract(locale='en-US', canonical_path='/about', consent='necessary-only')
    assert not necessary['analyticsEnabled']
    assert {'header', 'breadcrumb', 'footer', 'skip-link'} == set(necessary['navigation'])


def test_optional_capabilities_leave_no_residue():
    for name in ('search', 'builder', 'commerce', 'integrations'):
        state = disabled_capability(name)
        assert state['enabled'] is False
        assert all(
            not state[key]
            for key in (
                'routes',
                'navigation',
                'jobs',
                'schedules',
                'allocations',
                'credentials',
                'authority',
            )
        )
