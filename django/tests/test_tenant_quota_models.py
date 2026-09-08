from __future__ import annotations

import importlib
import inspect

import pytest
from django.core.exceptions import ValidationError

from sitecontent.models import TenantQuota, TenantQuotaReservation


def quota(site_id='tenant-one'):
    return TenantQuota(site_id=site_id, quota_key='jobs', limit=10, used=2, reserved=3)


def test_quota_accepts_only_bounded_usage():
    value = quota()
    value.clean()
    value.reserved = 9
    with pytest.raises(ValidationError, match='tenant_quota_capacity_invalid'):
        value.clean()


def test_reservation_requires_same_tenant_quota():
    reservation = TenantQuotaReservation(
        site_id='tenant-two',
        quota=quota(),
        reservation_id='job.reserve-001',
        amount=1,
    )
    with pytest.raises(ValidationError, match='tenant_quota_reservation_scope_invalid'):
        reservation.clean()


def test_quota_migrations_are_reversible_and_tenant_forced():
    models_migration = importlib.import_module(
        'sitecontent.migrations.0020_tenant_quota_persistence'
    )
    rls_migration = importlib.import_module(
        'sitecontent.migrations.0021_quota_rls_and_operations_worker_scope'
    )
    assert len(models_migration.Migration.operations) == 2
    assert all(operation.reversible for operation in rls_migration.Migration.operations)
    assert set(rls_migration.QUOTA_TABLES) == {
        'sitecontent_tenantquota',
        'sitecontent_tenantquotareservation',
    }
    source = inspect.getsource(rls_migration)
    assert 'FORCE ROW LEVEL SECURITY' in source
    assert "OR current_user" not in source
    assert 'GRANT ALL' not in source
