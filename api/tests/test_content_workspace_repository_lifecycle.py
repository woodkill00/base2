from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from api.repositories import content_workspace as repository


NOW = datetime(2026, 9, 2, 20, 0, tzinfo=UTC)
DEFINITION_ID = UUID(int=2104)
RECORD_ID = UUID(int=3104)
VIEW_ID = UUID(int=4104)
FIELDS: list[tuple[Any, ...]] = [("title", "short_text", True, False, None, {})]
RECORD = (RECORD_ID, "site-a", "article", "safe", "Safe", {"title": "Safe"}, "draft", 1, 2, NOW)


class QueueCursor:
    def __init__(self, *, ones=(), alls=()):
        self.ones = list(ones)
        self.alls = list(alls)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=()):
        self.calls.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.ones.pop(0) if self.ones else None

    def fetchall(self):
        return self.alls.pop(0) if self.alls else []


class Connection:
    def __init__(self, cursor):
        self.value = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def bind(monkeypatch, cursor):
    connection = Connection(cursor)

    @contextmanager
    def fake_db_conn(*, tenant_id):
        assert tenant_id == "site-a"
        yield connection

    monkeypatch.setattr(repository, "db_conn", fake_db_conn)
    return connection


def test_definition_detail_and_preview_cover_additive_backfill_and_lossy(monkeypatch):
    definition = (DEFINITION_ID, "site-a", "article", 2, "Article", "Safe", "draft", 1)
    field_detail = (
        "title",
        "Title",
        "short_text",
        True,
        False,
        None,
        {},
        {},
        True,
        True,
        "content.read",
        "content.write",
    )
    cursor = QueueCursor(ones=[definition], alls=[[field_detail]])
    bind(monkeypatch, cursor)
    result = repository.PostgresContentWorkspaceRepository().get_definition(
        site_id="site-a", type_key="article", version=2
    )
    assert result["fields"][0]["fieldKey"] == "title"
    assert result["fields"][0]["indexed"] is True

    cursor = QueueCursor(ones=[(DEFINITION_ID,), None], alls=[[FIELDS[0]]])
    bind(monkeypatch, cursor)
    additive = repository.PostgresContentWorkspaceRepository().preview_definition(
        site_id="site-a", type_key="article", version=1
    )
    assert additive["classification"] == "additive"
    assert additive["mutated"] is False and len(additive["digest"]) == 64

    old_id = UUID(int=2103)
    cursor = QueueCursor(
        ones=[(DEFINITION_ID,), (old_id,)],
        alls=[
            [("title", "short_text", True, False, {}), ("required_new", "short_text", True, False, {})],
            [("title", "short_text", True, False, {})],
        ],
    )
    bind(monkeypatch, cursor)
    backfill = repository.PostgresContentWorkspaceRepository().preview_definition(
        site_id="site-a", type_key="article", version=2
    )
    assert backfill["classification"] == "backfill_required"
    assert backfill["backfillFields"] == ["required_new"]

    cursor = QueueCursor(
        ones=[(DEFINITION_ID,), (old_id,)],
        alls=[
            [("title", "long_text", True, False, {})],
            [("title", "short_text", True, False, {}), ("removed", "short_text", False, False, {})],
        ],
    )
    bind(monkeypatch, cursor)
    lossy = repository.PostgresContentWorkspaceRepository().preview_definition(
        site_id="site-a", type_key="article", version=2
    )
    assert lossy["classification"] == "lossy"
    assert lossy["changedFields"] == ["title"] and lossy["removedFields"] == ["removed"]


def test_definition_not_found_and_publication_failures_roll_back(monkeypatch):
    cursor = QueueCursor(ones=[None])
    bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_not_found"):
        repository.PostgresContentWorkspaceRepository().get_definition(
            site_id="site-a", type_key="article", version=1
        )

    for locked, error in (
        (None, "content_not_found"),
        ((DEFINITION_ID, "published", 1), "content_schema_incompatible"),
        ((DEFINITION_ID, "draft", 2), "content_version_conflict"),
    ):
        cursor = QueueCursor(ones=[locked])
        connection = bind(monkeypatch, cursor)
        with pytest.raises(ValueError, match=error):
            repository.PostgresContentWorkspaceRepository().publish_definition(
                site_id="site-a",
                type_key="article",
                version=2,
                expected_lock_version=1,
                confirm_lossy=False,
                actor_ref="user:test",
            )
        assert connection.rollbacks == 1


def test_definition_publication_confirmation_and_retirement(monkeypatch):
    old_id = UUID(int=2103)
    cursor = QueueCursor(
        ones=[(DEFINITION_ID, "draft", 1), (DEFINITION_ID,), (old_id,)],
        alls=[
            [("title", "short_text", True, False, {}), ("required_new", "short_text", True, False, {})],
            [("title", "short_text", True, False, {})],
        ],
    )
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="lossy_confirmation_required"):
        repository.PostgresContentWorkspaceRepository().publish_definition(
            site_id="site-a",
            type_key="article",
            version=2,
            expected_lock_version=1,
            confirm_lossy=False,
            actor_ref="user:test",
        )
    assert connection.rollbacks == 1

    cursor = QueueCursor(
        ones=[
            (DEFINITION_ID, "draft", 1),
            (DEFINITION_ID,),
            None,
            ("article", 2, "published", 2),
        ],
        alls=[[FIELDS[0]]],
    )
    connection = bind(monkeypatch, cursor)
    published = repository.PostgresContentWorkspaceRepository().publish_definition(
        site_id="site-a",
        type_key="article",
        version=2,
        expected_lock_version=1,
        confirm_lossy=False,
        actor_ref="user:test",
    )
    assert published == {"typeKey": "article", "version": 2, "status": "published", "lockVersion": 2}
    assert connection.commits == 1

    cursor = QueueCursor(ones=[(DEFINITION_ID, "article", 2, "retired", 3)])
    connection = bind(monkeypatch, cursor)
    retired = repository.PostgresContentWorkspaceRepository().retire_definition(
        site_id="site-a",
        type_key="article",
        version=2,
        expected_lock_version=2,
        actor_ref="user:test",
    )
    assert retired["status"] == "retired" and connection.commits == 1

    cursor = QueueCursor(ones=[None])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_version_conflict"):
        repository.PostgresContentWorkspaceRepository().retire_definition(
            site_id="site-a",
            type_key="article",
            version=2,
            expected_lock_version=1,
            actor_ref="user:test",
        )
    assert connection.rollbacks == 1


def test_record_create_read_update_transition_history_and_restore(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    cursor = QueueCursor(ones=[(DEFINITION_ID, 1), RECORD], alls=[FIELDS])
    connection = bind(monkeypatch, cursor)
    created = repo.create_record(
        site_id="site-a",
        type_key="article",
        actor_ref="user:test",
        payload={"slug": "safe", "title": "Safe", "values": {"title": "Safe"}},
    )
    assert created["id"] == str(RECORD_ID) and connection.commits == 1

    cursor = QueueCursor(ones=[RECORD])
    bind(monkeypatch, cursor)
    assert repo.get_record(site_id="site-a", type_key="article", record_id=RECORD_ID)["version"] == 2
    cursor = QueueCursor(ones=[None])
    bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_not_found"):
        repo.get_record(site_id="site-a", type_key="article", record_id=RECORD_ID)

    existing = (RECORD_ID, 2, 1, {"title": "Safe"})
    updated_row = (*RECORD[:5], {"title": "Changed"}, *RECORD[6:8], 3, NOW)
    cursor = QueueCursor(ones=[existing, (DEFINITION_ID, 1), updated_row], alls=[FIELDS])
    connection = bind(monkeypatch, cursor)
    updated = repo.update_record(
        site_id="site-a",
        type_key="article",
        record_id=RECORD_ID,
        expected_version=2,
        actor_ref="user:test",
        values={"title": "Changed"},
    )
    assert updated["version"] == 3 and connection.commits == 1

    transitions = [
        {
            "action": "submit_review",
            "from": ["draft"],
            "to": "in_review",
            "permission": "content.write",
        }
    ]
    transitioned_row = (*RECORD[:6], "in_review", *RECORD[7:8], 3, NOW)
    cursor = QueueCursor(
        ones=[(RECORD_ID, 2, 1, {"title": "Safe"}, "draft", transitions), transitioned_row]
    )
    connection = bind(monkeypatch, cursor)
    transitioned = repo.transition_record(
        site_id="site-a",
        type_key="article",
        record_id=RECORD_ID,
        expected_version=2,
        actor_ref="user:test",
        action="submit_review",
        publish_at=None,
        timezone=None,
    )
    assert transitioned["state"] == "in_review" and connection.commits == 1

    cursor = QueueCursor(alls=[[(1, 1, "a" * 64, "update", None, NOW)]])
    bind(monkeypatch, cursor)
    history = repo.list_versions(site_id="site-a", type_key="article", record_id=RECORD_ID)
    assert history["items"][0]["createdAt"] == NOW.isoformat()

    restored_row = (*RECORD[:5], {"title": "Earlier"}, *RECORD[6:8], 3, NOW)
    cursor = QueueCursor(
        ones=[existing, ({"values": {"title": "Earlier"}},), (DEFINITION_ID, 1), restored_row],
        alls=[FIELDS],
    )
    connection = bind(monkeypatch, cursor)
    restored = repo.restore_record(
        site_id="site-a",
        type_key="article",
        record_id=RECORD_ID,
        version=1,
        expected_version=2,
        actor_ref="user:test",
    )
    assert restored["values"] == {"title": "Earlier"} and connection.commits == 1


def test_record_mutation_conflicts_and_invalid_transitions_are_closed(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    for existing, error in ((None, "content_not_found"), ((RECORD_ID, 3, 1, {}), "content_version_conflict")):
        cursor = QueueCursor(ones=[existing])
        connection = bind(monkeypatch, cursor)
        with pytest.raises(ValueError, match=error):
            repo.update_record(
                site_id="site-a",
                type_key="article",
                record_id=RECORD_ID,
                expected_version=2,
                actor_ref="user:test",
                values={"title": "Safe"},
            )
        assert connection.rollbacks == 1

    transitions = [{"action": "publish", "from": ["in_review"], "to": "published"}]
    cursor = QueueCursor(ones=[(RECORD_ID, 2, 1, {}, "draft", transitions)])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_transition_invalid"):
        repo.transition_record(
            site_id="site-a",
            type_key="article",
            record_id=RECORD_ID,
            expected_version=2,
            actor_ref="user:test",
            action="publish",
            publish_at=None,
            timezone=None,
        )
    assert connection.rollbacks == 1


def test_saved_view_crud_is_tenant_owner_schema_and_version_bound(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    query = {"filters": [], "sort": ["slug"], "fields": ["title"], "expand": [], "limit": 25}
    view_row = (VIEW_ID, "Safe", query, "private", [], 1, 1)

    cursor = QueueCursor(alls=[[view_row]])
    bind(monkeypatch, cursor)
    listed = repo.list_views(
        site_id="site-a", type_key="article", owner_ref="user:test", caller_role="editor"
    )
    assert listed["items"][0]["id"] == str(VIEW_ID)

    cursor = QueueCursor(ones=[(DEFINITION_ID, 1), (VIEW_ID, "Safe", "private", 1, 1)], alls=[FIELDS])
    connection = bind(monkeypatch, cursor)
    created = repo.create_view(
        site_id="site-a",
        type_key="article",
        owner_ref="user:test",
        payload={"title": "Safe", "query": query, "visibility": "private", "shared_roles": []},
    )
    assert created["lockVersion"] == 1 and connection.commits == 1

    cursor = QueueCursor(ones=[(*view_row, 1)])
    bind(monkeypatch, cursor)
    detail = repo.get_view(
        site_id="site-a",
        type_key="article",
        view_id=VIEW_ID,
        owner_ref="user:test",
        caller_role=None,
    )
    assert detail["currentSchemaVersion"] == 1

    updated_row = (VIEW_ID, "Changed", query, "role_shared", ["editor"], 1, 2)
    cursor = QueueCursor(ones=[view_row, (DEFINITION_ID, 1), updated_row], alls=[FIELDS])
    connection = bind(monkeypatch, cursor)
    updated = repo.update_view(
        site_id="site-a",
        type_key="article",
        view_id=VIEW_ID,
        owner_ref="user:test",
        expected_version=1,
        payload={"title": "Changed", "visibility": "role_shared", "shared_roles": ["editor"]},
    )
    assert updated["visibility"] == "role_shared" and connection.commits == 1

    cursor = QueueCursor(ones=[(VIEW_ID,)])
    connection = bind(monkeypatch, cursor)
    deleted = repo.delete_view(
        site_id="site-a",
        type_key="article",
        view_id=VIEW_ID,
        owner_ref="user:test",
        expected_version=2,
    )
    assert deleted == {"id": str(VIEW_ID), "deleted": True} and connection.commits == 1


def test_saved_view_invalid_owner_version_fields_and_visibility_roll_back(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    query = {"filters": [], "sort": ["slug"], "fields": [], "expand": [], "limit": 25}
    for row, expected, payload in (
        (None, "content_not_found", {}),
        ((VIEW_ID, "Safe", query, "private", [], 1, 2), "content_version_conflict", {}),
        (
            (VIEW_ID, "Safe", query, "private", [], 1, 1),
            "saved_view_roles_invalid",
            {"visibility": "private", "shared_roles": ["editor"]},
        ),
    ):
        cursor = QueueCursor(ones=[row])
        connection = bind(monkeypatch, cursor)
        with pytest.raises(ValueError, match=expected):
            repo.update_view(
                site_id="site-a",
                type_key="article",
                view_id=VIEW_ID,
                owner_ref="user:test",
                expected_version=1,
                payload=payload,
            )
        assert connection.rollbacks == 1

    cursor = QueueCursor(ones=[None])
    bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_not_found"):
        repo.get_view(
            site_id="site-a",
            type_key="article",
            view_id=VIEW_ID,
            owner_ref="user:test",
            caller_role=None,
        )
    cursor = QueueCursor(ones=[None])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_version_conflict"):
        repo.delete_view(
            site_id="site-a",
            type_key="article",
            view_id=VIEW_ID,
            owner_ref="user:test",
            expected_version=1,
        )
    assert connection.rollbacks == 1
