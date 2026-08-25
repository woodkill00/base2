import pytest

from api.services.data_rights import isolated_restore_preview, receipt_digest, verify_receipt


def test_receipt_is_deterministic_bound_and_isolated_preview_only():
    payload = {'account': {'email': 'owner@example.test'}, 'schema_version': 1}
    receipt = {'operation_id': 'op-1', 'tenant_id': 'tenant-a', 'user_id': 'user-1'}
    digest = receipt_digest(payload=payload, key='pepper', **receipt)
    assert digest == receipt_digest(payload=payload, key='pepper', **receipt)
    assert verify_receipt(payload=payload, key='pepper', digest=digest, **receipt)
    assert isolated_restore_preview(
        payload=payload, expected_digest=digest, receipt=receipt, key='pepper'
    ) == payload
    for changed in (
        {**payload, 'schema_version': 2},
        {'account': {'email': 'attacker@example.test'}, 'schema_version': 1},
    ):
        assert not verify_receipt(payload=changed, key='pepper', digest=digest, **receipt)
    with pytest.raises(ValueError, match='live_restore_forbidden'):
        isolated_restore_preview(
            payload=payload, expected_digest=digest, receipt=receipt,
            key='pepper', target='production',
        )


def test_wrong_receipt_binding_and_key_fail_closed():
    payload = {'schema_version': 1}
    receipt = {'operation_id': 'op-1', 'tenant_id': 'tenant-a', 'user_id': 'user-1'}
    digest = receipt_digest(payload=payload, key='pepper', **receipt)
    for field, value in (
        ('operation_id', 'op-2'), ('tenant_id', 'tenant-b'), ('user_id', 'user-2')
    ):
        changed = {**receipt, field: value}
        with pytest.raises(ValueError, match='export_integrity_failed'):
            isolated_restore_preview(
                payload=payload, expected_digest=digest, receipt=changed, key='pepper'
            )
    with pytest.raises(ValueError, match='export_integrity_failed'):
        isolated_restore_preview(
            payload=payload, expected_digest=digest, receipt=receipt, key='wrong'
        )
