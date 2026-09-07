from __future__ import annotations

import importlib
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.models import validate_operations_dimensions
from sitecontent.models import (
    OperationsAlertDelivery,
    OperationsHealthSample,
    OperationsIncident,
    OperationsIncidentEvent,
    OperationsObjective,
    OperationsService,
    OperationsSyntheticRun,
)


def service(site_id="tenant-one"):
    return OperationsService(
        site_id=site_id,
        service_key="api.health",
        environment="staging",
    )


def incident(site_id="tenant-one"):
    now = timezone.now()
    return OperationsIncident(
        site_id=site_id,
        fingerprint="a" * 64,
        severity="high",
        state="firing",
        summary_code="api.unavailable",
        first_observed_at=now,
        last_observed_at=now,
    )


def test_operations_dimensions_are_bounded_and_secret_free():
    validate_operations_dimensions({"region": "test", "attempt": 2})
    hostile = [
        {"password": "not-recorded"},
        {"nested": {"value": "no"}},
        {f"key-{index}": index for index in range(17)},
        {"region": "x" * 201},
    ]
    for value in hostile:
        with pytest.raises(ValidationError):
            validate_operations_dimensions(value)


def test_health_requires_matching_tenant_and_freshness_window():
    now = timezone.now()
    valid = OperationsHealthSample(
        site_id="tenant-one",
        service=service(),
        state="healthy",
        code="api.ready",
        observed_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    valid.clean()
    wrong = OperationsHealthSample(
        site_id="tenant-two",
        service=service(),
        state="healthy",
        code="api.ready",
        observed_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    with pytest.raises(ValidationError, match="operations_health_scope_invalid"):
        wrong.clean()
    valid.expires_at = now
    with pytest.raises(ValidationError, match="operations_health_expiry_invalid"):
        valid.clean()


def test_synthetic_terminal_state_binds_commit_digest_and_completion():
    now = timezone.now()
    run = OperationsSyntheticRun(
        site_id="tenant-one",
        journey_key="member.login",
        role="member",
        source_commit="b" * 40,
        status="passed",
        result_digest="c" * 64,
        started_at=now,
        completed_at=now + timedelta(seconds=2),
    )
    run.clean()
    run.completed_at = None
    with pytest.raises(ValidationError, match="operations_synthetic_state_invalid"):
        run.clean()


def test_objective_bounds_are_fail_closed():
    objective = OperationsObjective(
        site_id="tenant-one",
        objective_key="api.availability",
        indicator="api.success_ratio",
        target=Decimal("0.99900"),
        warning_threshold=Decimal("0.99500"),
        window_minutes=60,
    )
    objective.clean()
    objective.warning_threshold = Decimal("1.00000")
    with pytest.raises(ValidationError, match="operations_objective_warning_invalid"):
        objective.clean()


def test_incident_resolution_and_tenant_links_are_consistent():
    value = incident()
    value.clean()
    value.state = "resolved"
    with pytest.raises(ValidationError, match="operations_incident_resolution_invalid"):
        value.clean()
    event = OperationsIncidentEvent(
        site_id="tenant-two",
        incident=incident(),
        event_key="incident.observed",
        occurred_at=timezone.now(),
    )
    with pytest.raises(ValidationError, match="operations_event_scope_invalid"):
        event.clean()


def test_alert_delivery_is_tenant_attempt_and_digest_bound():
    delivery = OperationsAlertDelivery(
        site_id="tenant-two",
        incident=incident(),
        expires_at=timezone.now() + timedelta(minutes=15),
        attempts=6,
        maximum_attempts=5,
        receipt_digest="bad",
    )
    with pytest.raises(ValidationError):
        delivery.clean()


def test_operations_migrations_are_forward_and_reverse_capable():
    models_migration = importlib.import_module(
        "sitecontent.migrations.0018_production_operations_center"
    )
    rls_migration = importlib.import_module("sitecontent.migrations.0019_operations_center_rls")
    self_tables = set(rls_migration.TABLES)
    expected = {
        "sitecontent_operationsservice",
        "sitecontent_operationshealthsample",
        "sitecontent_operationssyntheticrun",
        "sitecontent_operationsobjective",
        "sitecontent_operationsincident",
        "sitecontent_operationsincidentevent",
        "sitecontent_operationsalertdelivery",
    }
    assert expected == self_tables
    assert len(models_migration.Migration.operations) == 7
    assert all(operation.reversible for operation in rls_migration.Migration.operations)
