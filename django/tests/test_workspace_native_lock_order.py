"""Native helpers must use the same lock order as the API policy effects."""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import QuerySet

from sitecontent import models

pytestmark = pytest.mark.django_db


def test_postgres_native_lock_is_transaction_scoped_and_never_sets_actor(monkeypatch):
    module = importlib.import_module("sitecontent.policy_locks")
    cursor = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = cursor
    connection = SimpleNamespace(vendor="postgresql", in_atomic_block=True, cursor=lambda: context)
    monkeypatch.setattr(module, "connection", connection)
    module.begin_workspace_policy_effect()
    cursor.execute.assert_called_once_with(
        "SELECT pg_advisory_xact_lock(hashtext(%s))", ("base2-workspace-policy-v1",)
    )


def test_postgres_native_lock_rejects_autocommit(monkeypatch):
    module = importlib.import_module("sitecontent.policy_locks")
    cursor = MagicMock()
    monkeypatch.setattr(
        module,
        "connection",
        SimpleNamespace(vendor="postgresql", in_atomic_block=False, cursor=cursor),
    )
    with pytest.raises(RuntimeError, match="workspace_policy_transaction_required"):
        module.begin_workspace_policy_effect()
    cursor.assert_not_called()


def test_sqlite_diagnostics_do_not_pretend_to_acquire_postgres_lock(monkeypatch):
    module = importlib.import_module("sitecontent.policy_locks")
    cursor = MagicMock()
    monkeypatch.setattr(module, "connection", SimpleNamespace(vendor="sqlite", cursor=cursor))
    module.begin_workspace_policy_effect()
    cursor.assert_not_called()


@pytest.mark.parametrize("operation", ["update", "transition", "restore", "definition"])
def test_native_advisory_lock_precedes_row_lock(monkeypatch, operation):
    record = models.ContentRecord.objects.create(
        site_id="native-locks", content_type="page", slug="record", title="Record"
    )
    definition = models.ContentTypeDefinition.objects.create(
        site_id="native-locks", type_key="article", name="Article"
    )
    events = []
    original = QuerySet.select_for_update

    def row_lock(query, *args, **kwargs):
        events.append("row")
        return original(query, *args, **kwargs)

    monkeypatch.setattr(models, "begin_workspace_policy_effect", lambda: events.append("policy"))
    monkeypatch.setattr(QuerySet, "select_for_update", row_lock)
    with pytest.raises(ValidationError, match="version_conflict"):
        if operation == "update":
            record.update_values({}, expected_version=99)
        elif operation == "transition":
            record.transition_action("submit_review", expected_version=99)
        elif operation == "restore":
            record.restore_version(1, expected_version=99)
        else:
            definition.publish(expected_lock_version=99)
    assert events[:2] == ["policy", "row"]


@pytest.mark.django_db(transaction=True)
def test_legacy_transition_enters_atomic_policy_lock_before_revision(monkeypatch):
    record = models.ContentRecord.objects.create(
        site_id="native-locks", content_type="page", slug="legacy", title="Legacy"
    )
    events = []

    def policy_lock():
        assert connection.in_atomic_block
        events.append("policy")

    def revision(*args, **kwargs):
        events.append("revision")
        raise RuntimeError("stop_before_revision_write")

    monkeypatch.setattr(models, "begin_workspace_policy_effect", policy_lock)
    monkeypatch.setattr(record, "create_revision", revision)
    assert not connection.in_atomic_block
    with pytest.raises(RuntimeError, match="stop_before_revision_write"):
        record.transition_to("published", actor_ref="operator:not-a-public-identity")
    assert events == ["policy", "revision"]
    assert not connection.in_atomic_block
    record.refresh_from_db()
    assert record.state == "draft"


def test_incoming_relationship_helper_locks_before_relationship_rows(monkeypatch):
    record = models.ContentRecord.objects.create(
        site_id="native-locks", content_type="page", slug="incoming", title="Incoming"
    )
    events = []
    original = QuerySet.select_for_update

    def row_lock(query, *args, **kwargs):
        events.append("row")
        return original(query, *args, **kwargs)

    monkeypatch.setattr(models, "begin_workspace_policy_effect", lambda: events.append("policy"))
    monkeypatch.setattr(QuerySet, "select_for_update", row_lock)
    with transaction.atomic():
        record._apply_incoming_deletion_policies(actor_ref="operator:test")
    assert events[:2] == ["policy", "row"]


def test_native_lock_errors_are_not_a_permissive_fallback(monkeypatch):
    module = importlib.import_module("sitecontent.policy_locks")
    cursor = MagicMock()
    cursor.execute.side_effect = RuntimeError("database_lock_failed")
    context = MagicMock()
    context.__enter__.return_value = cursor
    monkeypatch.setattr(
        module,
        "connection",
        SimpleNamespace(vendor="postgresql", in_atomic_block=True, cursor=lambda: context),
    )
    with pytest.raises(RuntimeError, match="database_lock_failed"):
        module.begin_workspace_policy_effect()
