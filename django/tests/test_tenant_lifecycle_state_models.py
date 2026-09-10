import uuid
from pathlib import Path

import pytest

from sitecontent.models import TenantLifecycleEvent, TenantLifecycleState


@pytest.mark.django_db
def test_tenant_lifecycle_state_and_event_validate_tenant_private_history():
    operation_id = uuid.UUID("00000000-0000-4000-8000-000000000106")
    state = TenantLifecycleState(
        site_id="tenant-one",
        state="active",
        owner_ref="owner-one",
        configuration={"locale": "en"},
        revision=2,
        last_operation_id=operation_id,
        last_receipt_digest="a" * 64,
    )
    state.full_clean()
    event = TenantLifecycleEvent(
        site_id="tenant-one",
        operation_id=operation_id,
        operation="transition",
        from_state="provisioning",
        to_state="active",
        actor_ref="owner-one",
        revision=2,
        receipt_digest="a" * 64,
    )
    event.full_clean()


def test_tenant_lifecycle_event_migration_is_append_only_at_database_boundary():
    migration = (
        Path(__file__).parents[1]
        / "sitecontent"
        / "migrations"
        / "0029_tenant_lifecycle_state.py"
    ).read_text(encoding="utf-8")
    assert 'GRANT SELECT, INSERT ON TABLE "{EVENT_TABLE}"' in migration
    assert "tenant_lifecycle_event_immutable" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
