from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest

from api.repositories import content_workspace as repository


NOW = datetime(2026, 9, 2, 21, 0, tzinfo=UTC)
RECORD_ID = UUID(int=3104)
TARGET_ID = UUID(int=3204)
DEFINITION_ID = UUID(int=2104)
ASSET_ID = UUID(int=7104)
RELATIONSHIP_ID = UUID(int=8104)
RECORD = (RECORD_ID, 2, 1, {"title": "Safe"}, DEFINITION_ID)


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


def test_asset_upload_creation_and_detail_are_grant_and_derivative_bound(monkeypatch):
    monkeypatch.setattr(repository.settings, "TOKEN_PEPPER", "synthetic-test-pepper-104")
    repo = repository.PostgresContentWorkspaceRepository()
    cursor = QueueCursor(ones=[None, (0, 0, 0, 0), (ASSET_ID, "pending")])
    connection = bind(monkeypatch, cursor)
    created = repo.create_asset_upload(
        site_id="site-a",
        owner_ref="user:test",
        payload={
            "filename": "safe.png",
            "media_type": "image/png",
            "byte_size": 32,
            "sha256": "a" * 64,
        },
        idempotency_key="asset-upload-104",
        maximum_stored_bytes=1024,
        maximum_active_uploads=10,
        maximum_pending_processing=10,
    )
    assert created["id"] == str(ASSET_ID)
    assert created["status"] == "pending" and created["expiresIn"] == 300
    assert "site-a" not in created["uploadGrant"]
    assert connection.commits == 1
    quota_query = cursor.calls[2]
    assert "sitecontent_mediauploadsession" in quota_query[0]
    assert "expires_at>NOW()" in quota_query[0]
    assert quota_query[1] == ("site-a", "site-a", "site-a", "site-a")

    row = (
        ASSET_ID,
        "safe.png",
        "image/png",
        32,
        "a" * 64,
        "validated",
        "Creator",
        {"width": 1, "height": 1},
        NOW,
        "b" * 64,
        "image/png",
    )
    cursor = QueueCursor(ones=[row])
    bind(monkeypatch, cursor)
    detail = repo.get_asset(site_id="site-a", asset_id=ASSET_ID, requester_ref="user:reader")
    assert detail["downloadGrant"] and detail["expiresIn"] == 60
    assert detail["updatedAt"] == NOW.isoformat()

    pending = (*row[:5], "quarantined", *row[6:9], None, None)
    cursor = QueueCursor(ones=[pending])
    bind(monkeypatch, cursor)
    detail = repo.get_asset(site_id="site-a", asset_id=ASSET_ID, requester_ref="user:reader")
    assert "downloadGrant" not in detail

    cursor = QueueCursor(ones=[None])
    bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_not_found"):
        repo.get_asset(site_id="site-a", asset_id=ASSET_ID, requester_ref="user:reader")


def test_asset_upload_replay_is_exact_and_quota_admission_is_atomic(monkeypatch):
    monkeypatch.setattr(repository.settings, "TOKEN_PEPPER", "synthetic-test-pepper-104")
    repo = repository.PostgresContentWorkspaceRepository()
    payload = {
        "filename": "safe.png", "media_type": "image/png", "byte_size": 32,
        "sha256": "a" * 64,
    }
    replay = (ASSET_ID, "pending", "safe.png", "image/png", 32, "a" * 64)
    cursor = QueueCursor(ones=[replay])
    connection = bind(monkeypatch, cursor)
    result = repo.create_asset_upload(
        site_id="site-a", owner_ref="user:test", payload=payload,
        idempotency_key="asset-upload-104", maximum_stored_bytes=1024,
        maximum_active_uploads=10, maximum_pending_processing=10,
    )
    assert result["replayed"] is True and result["id"] == str(ASSET_ID)
    assert connection.commits == 1
    assert "pg_advisory_xact_lock" in cursor.calls[0][0]

    cursor = QueueCursor(ones=[(*replay[:2], "other.png", *replay[3:])])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_idempotency_conflict"):
        repo.create_asset_upload(
            site_id="site-a", owner_ref="user:test", payload=payload,
            idempotency_key="asset-upload-104", maximum_stored_bytes=1024,
            maximum_active_uploads=10, maximum_pending_processing=10,
        )
    assert connection.rollbacks == 1

    cursor = QueueCursor(ones=[None, (800, 200, 3, 0)])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_quota_storage_exceeded"):
        repo.create_asset_upload(
            site_id="site-a", owner_ref="user:test", payload=payload,
            idempotency_key="asset-upload-105", maximum_stored_bytes=1024,
            maximum_active_uploads=10, maximum_pending_processing=10,
        )
    assert connection.rollbacks == 1


def test_upload_grant_preflight_is_owner_bound_and_stateless(monkeypatch):
    monkeypatch.setattr(repository.settings, "TOKEN_PEPPER", "synthetic-test-pepper-104")
    repo = repository.PostgresContentWorkspaceRepository()
    scope = {
        "site": "site-a",
        "owner": "user:test",
        "asset": str(ASSET_ID),
        "sha256": "a" * 64,
        "bytes": 32,
        "purpose": "asset-upload",
    }
    grant = repository.CursorCodec(
        str(repository.settings.TOKEN_PEPPER), ttl_seconds=300
    ).encode(scope=scope, position={"assetId": str(ASSET_ID)})
    cursor = QueueCursor(ones=[(32, "a" * 64, "pending")])
    bind(monkeypatch, cursor)
    assert repo.validate_asset_upload_grant(
        site_id="site-a",
        asset_id=ASSET_ID,
        owner_ref="user:test",
        upload_grant=grant,
    ) == {"expectedBytes": 32}
    assert cursor.calls[0][1] == (str(ASSET_ID), "site-a", "user:test")

    cursor = QueueCursor(ones=[(32, "a" * 64, "pending")])
    bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_upload_grant_invalid"):
        repo.validate_asset_upload_grant(
            site_id="site-a",
            asset_id=ASSET_ID,
            owner_ref="user:test",
            upload_grant=grant + "x",
        )

def test_record_lock_and_bump_enforce_presence_and_version():
    repo = repository.PostgresContentWorkspaceRepository()
    cursor = QueueCursor(ones=[RECORD])
    assert repo._lock_record(
        cursor,
        site_id="site-a",
        type_key="article",
        record_id=RECORD_ID,
        expected_version=2,
    ) == RECORD

    for row, error in ((None, "content_not_found"), (RECORD, "content_version_conflict")):
        cursor = QueueCursor(ones=[row])
        with pytest.raises(ValueError, match=error):
            repo._lock_record(
                cursor,
                site_id="site-a",
                type_key="article",
                record_id=RECORD_ID,
                expected_version=3,
            )

    cursor = QueueCursor(ones=[(3,)])
    version = repo._bump_record(
        cursor,
        record=RECORD,
        site_id="site-a",
        actor_ref="user:test",
        action="safe_change",
    )
    assert version == 3
    assert "sitecontent_contentrevision" in cursor.calls[0][0]


def test_asset_binding_and_unbinding_are_versioned_transactions(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    binding_id = UUID(int=9104)
    cursor = QueueCursor(
        ones=[RECORD, ("image/png", "ready"), ("image",), (binding_id,), (3,)]
    )
    connection = bind(monkeypatch, cursor)
    bound = repo.bind_asset(
        site_id="site-a",
        type_key="article",
        record_id=RECORD_ID,
        field_key="hero",
        expected_version=2,
        actor_ref="user:test",
        payload={"asset_id": ASSET_ID, "alt_text": "Safe image", "order": 1},
    )
    assert UUID(bound["id"]) and bound["recordVersion"] == 3
    assert connection.commits == 1
    assert "owner_ref=%s OR visibility" in cursor.calls[1][0]
    assert cursor.calls[1][1] == (str(ASSET_ID), "site-a", "user:test")

    cursor = QueueCursor(ones=[RECORD, (binding_id,), (3,)])
    connection = bind(monkeypatch, cursor)
    unbound = repo.unbind_asset(
        site_id="site-a",
        type_key="article",
        record_id=RECORD_ID,
        field_key="hero",
        asset_id=ASSET_ID,
        expected_version=2,
        actor_ref="user:test",
    )
    assert unbound == {"deleted": True, "recordVersion": 3}
    assert connection.commits == 1
    assert "EXISTS" in cursor.calls[1][0]
    assert "asset.owner_ref=%s OR asset.visibility" in cursor.calls[1][0]
    assert cursor.calls[1][1] == (
        "site-a", str(RECORD_ID), "hero", str(ASSET_ID), "user:test"
    )


def test_private_asset_binding_and_unbinding_fail_closed_for_non_owner(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()

    cursor = QueueCursor(ones=[RECORD, None])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_asset_quarantined"):
        repo.bind_asset(
            site_id="site-a",
            type_key="article",
            record_id=RECORD_ID,
            field_key="hero",
            expected_version=2,
            actor_ref="user:other",
            payload={"asset_id": ASSET_ID, "alt_text": "Private image"},
        )
    assert connection.rollbacks == 1
    assert cursor.calls[1][1][-1] == "user:other"

    cursor = QueueCursor(ones=[RECORD, None])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_not_found"):
        repo.unbind_asset(
            site_id="site-a",
            type_key="article",
            record_id=RECORD_ID,
            field_key="hero",
            asset_id=ASSET_ID,
            expected_version=2,
            actor_ref="user:other",
        )
    assert connection.rollbacks == 1
    assert cursor.calls[1][1][-1] == "user:other"


@pytest.mark.parametrize(
    ("asset", "field", "alt_text", "error"),
    [
        (None, ("image",), "Safe", "content_asset_quarantined"),
        (("image/png", "quarantined"), ("image",), "Safe", "content_asset_quarantined"),
        (("image/png", "validated"), None, "Safe", "content_schema_invalid"),
        (("image/png", "validated"), ("short_text",), "Safe", "content_schema_invalid"),
        (("image/png", "validated"), ("image",), " ", "content_schema_invalid"),
    ],
)
def test_asset_binding_rejects_unsafe_asset_or_field(monkeypatch, asset, field, alt_text, error):
    cursor = QueueCursor(ones=[RECORD, asset, field])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match=error):
        repository.PostgresContentWorkspaceRepository().bind_asset(
            site_id="site-a",
            type_key="article",
            record_id=RECORD_ID,
            field_key="hero",
            expected_version=2,
            actor_ref="user:test",
            payload={"asset_id": ASSET_ID, "alt_text": alt_text},
        )
    assert connection.rollbacks == 1


def test_unbind_missing_asset_rolls_back(monkeypatch):
    cursor = QueueCursor(ones=[RECORD, None])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_not_found"):
        repository.PostgresContentWorkspaceRepository().unbind_asset(
            site_id="site-a",
            type_key="article",
            record_id=RECORD_ID,
            field_key="hero",
            asset_id=ASSET_ID,
            expected_version=2,
            actor_ref="user:test",
        )
    assert connection.rollbacks == 1


def test_relationship_listing_creation_and_deletion(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    cursor = QueueCursor(
        alls=[[(RELATIONSHIP_ID, "related", TARGET_ID, 0, "restrict", "article")]]
    )
    bind(monkeypatch, cursor)
    listed = repo.list_relationships(site_id="site-a", type_key="article", record_id=RECORD_ID)
    assert listed["items"] == [
        {
            "id": str(RELATIONSHIP_ID),
            "fieldKey": "related",
            "targetId": str(TARGET_ID),
            "order": 0,
            "deletionPolicy": "restrict",
            "targetType": "article",
        }
    ]

    cursor = QueueCursor(
        ones=[RECORD, ("article",), ("references", {"targetType": "article"}), (0,), None, (3,)]
    )
    connection = bind(monkeypatch, cursor)
    created = repo.create_relationship(
        site_id="site-a",
        type_key="article",
        record_id=RECORD_ID,
        expected_version=2,
        actor_ref="user:test",
        payload={"target_id": TARGET_ID, "field_key": "related"},
    )
    assert created["recordVersion"] == 3 and UUID(created["id"])
    assert connection.commits == 1

    cursor = QueueCursor(ones=[RECORD, (RELATIONSHIP_ID,), (3,)])
    connection = bind(monkeypatch, cursor)
    deleted = repo.delete_relationship(
        site_id="site-a",
        type_key="article",
        record_id=RECORD_ID,
        relationship_id=RELATIONSHIP_ID,
        expected_version=2,
        actor_ref="user:test",
    )
    assert deleted == {"deleted": True, "recordVersion": 3}
    assert connection.commits == 1


def test_relationship_expansion_uses_one_bounded_query_regardless_of_result_count(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    rows = [
        (UUID(int=8200 + number), "related", UUID(int=8300 + number), number, "restrict", "article")
        for number in range(25)
    ]
    cursor = QueueCursor(alls=[rows])
    bind(monkeypatch, cursor)
    result = repo.list_relationships(site_id="site-a", type_key="article", record_id=RECORD_ID)
    assert len(result["items"]) == 25
    assert len(cursor.calls) == 1
    assert "LIMIT 200" in cursor.calls[0][0]

@pytest.mark.parametrize(
    ("payload", "ones", "error"),
    [
        (
            {"target_id": RECORD_ID, "field_key": "related"},
            [RECORD],
            "relationship_scope_invalid",
        ),
        (
            {"target_id": TARGET_ID, "field_key": "related"},
            [RECORD, None],
            "content_not_found",
        ),
        (
            {"target_id": TARGET_ID, "field_key": "related"},
            [RECORD, ("article",), None],
            "content_schema_invalid",
        ),
        (
            {"target_id": TARGET_ID, "field_key": "related"},
            [RECORD, ("article",), ("short_text", {})],
            "content_schema_invalid",
        ),
        (
            {"target_id": TARGET_ID, "field_key": "related"},
            [RECORD, ("person",), ("reference", {"targetType": "article"})],
            "relationship_target_type_invalid",
        ),
        (
            {"target_id": TARGET_ID, "field_key": "related"},
            [RECORD, ("article",), ("reference", {}), (1,)],
            "relationship_cardinality_invalid",
        ),
        (
            {"target_id": TARGET_ID, "field_key": "related"},
            [RECORD, ("article",), ("references", {"maximumItems": 5}), (0,), (1,)],
            "relationship_cycle_invalid",
        ),
    ],
)
def test_relationship_creation_rejects_invalid_graphs(monkeypatch, payload, ones, error):
    cursor = QueueCursor(ones=ones)
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match=error):
        repository.PostgresContentWorkspaceRepository().create_relationship(
            site_id="site-a",
            type_key="article",
            record_id=RECORD_ID,
            expected_version=2,
            actor_ref="user:test",
            payload=payload,
        )
    assert connection.rollbacks == 1


def test_relationship_delete_missing_rolls_back(monkeypatch):
    cursor = QueueCursor(ones=[RECORD, None])
    connection = bind(monkeypatch, cursor)
    with pytest.raises(ValueError, match="content_not_found"):
        repository.PostgresContentWorkspaceRepository().delete_relationship(
            site_id="site-a",
            type_key="article",
            record_id=RECORD_ID,
            relationship_id=RELATIONSHIP_ID,
            expected_version=2,
            actor_ref="user:test",
        )
    assert connection.rollbacks == 1
