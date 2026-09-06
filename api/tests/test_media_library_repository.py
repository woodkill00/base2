from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest

from api.repositories import media_library as repository


class Cursor:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=()):
        self.calls.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        result = list(self.rows)
        self.rows.clear()
        return result


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


class SequenceCursor(Cursor):
    def __init__(self, responses):
        super().__init__()
        self.responses = list(responses)
        self.rowcount = 1

    def execute(self, sql, params=()):
        super().execute(sql, params)
        response = self.responses.pop(0) if self.responses else []
        self.rows = list(response)


def bind(monkeypatch, connection):
    scopes = []

    @contextmanager
    def fake_db_conn(*, tenant_id):
        scopes.append(tenant_id)
        yield connection

    monkeypatch.setattr(repository, "db_conn", fake_db_conn)
    return scopes


def asset_row(number=1):
    return (
        UUID(int=number), "safe.png", "image/png", 10, "a" * 64, "ready",
        "private", 2, datetime(2026, 9, 6, tzinfo=UTC),
    )


def test_list_assets_is_tenant_scoped_parameterized_and_stable(monkeypatch):
    cursor = Cursor([asset_row(1), asset_row(2)])
    scopes = bind(monkeypatch, Connection(cursor))
    result = repository.PostgresMediaLibraryRepository().list_assets(
        site_id="site-a", limit=1, offset=0, state="ready",
        media_type="image/png", search="safe",
    )
    assert scopes == ["site-a"]
    sql, params = cursor.calls[0]
    assert "site_id=%s" in sql and "ORDER BY updated_at DESC, id DESC" in sql
    assert "safe" not in sql and params == ("site-a", "ready", "image/png", "%safe%", 2, 0)
    assert result["nextOffset"] == 1 and len(result["items"]) == 1


def test_get_asset_never_selects_storage_keys(monkeypatch):
    cursor = Cursor([asset_row()])
    bind(monkeypatch, Connection(cursor))
    result = repository.PostgresMediaLibraryRepository().get_asset(
        site_id="site-a", asset_id=UUID(int=1)
    )
    assert result["id"] == str(UUID(int=1)) and result["variants"] == []
    assert all("storage_key" not in sql for sql, _ in cursor.calls)


def test_metadata_update_is_version_bound_and_transactional(monkeypatch):
    cursor = Cursor([(3, "image/png"), (5,), (4,)])
    connection = Connection(cursor)
    bind(monkeypatch, connection)
    result = repository.PostgresMediaLibraryRepository().update_metadata(
        site_id="site-a", asset_id=UUID(int=1), actor_ref="user:test", expected_version=3,
        payload={
            "locale": "en", "altText": "Safe preview", "decorative": False,
            "caption": "", "credit": "", "licenseCode": "", "focalX": None,
            "focalY": None, "visibility": "private",
        },
    )
    assert result == {"id": str(UUID(int=1)), "revision": 5, "version": 4}
    assert connection.commits == 1 and connection.rollbacks == 0
    assert "FOR UPDATE" in cursor.calls[0][0]


def test_metadata_update_rolls_back_on_conflict(monkeypatch):
    cursor = Cursor([(4, "image/png")])
    connection = Connection(cursor)
    bind(monkeypatch, connection)
    with pytest.raises(ValueError, match="media_version_conflict"):
        repository.PostgresMediaLibraryRepository().update_metadata(
            site_id="site-a", asset_id=UUID(int=1), actor_ref="user:test", expected_version=3,
            payload={},
        )
    assert connection.commits == 0 and connection.rollbacks == 1


def test_reference_inventory_and_destructive_preview_are_scope_bound(monkeypatch):
    reference = (UUID(int=2), "content-record", UUID(int=3), "hero", "published", "public", True, 1)
    cursor = SequenceCursor([
        [reference],
        [(2, "ready")],
        [("content-record", UUID(int=3), "hero", "published", True)],
        [("legal_hold",)],
        [(1, "a" * 64, 10)],
    ])
    bind(monkeypatch, Connection(cursor))
    repo = repository.PostgresMediaLibraryRepository()
    inventory = repo.list_references(site_id="site-a", asset_id=UUID(int=1))
    preview = repo.destructive_preview(site_id="site-a", asset_id=UUID(int=1))
    assert inventory["items"][0]["ownerState"] == "published"
    assert preview["allowed"] is False
    assert preview["activeHolds"] == ["legal_hold"]
    assert all(params[0] == "site-a" for _sql, params in cursor.calls)


def test_transition_is_versioned_transactional_and_emits_outbox(monkeypatch):
    cursor = SequenceCursor([[(2, "ready")], [(UUID(int=4),)], [(3,)]])
    connection = Connection(cursor)
    bind(monkeypatch, connection)
    result = repository.PostgresMediaLibraryRepository().transition_asset(
        site_id="site-a", asset_id=UUID(int=1), actor_ref="user:test",
        target="archived", expected_version=2, idempotency_key="archive-1",
    )
    assert result == {
        "id": str(UUID(int=1)), "status": "archived", "version": 3, "replayed": False,
    }
    assert connection.commits == 1
    assert any("sitecontent_mediaoutboxevent" in sql for sql, _params in cursor.calls)


def test_transition_blocks_destructive_reference_and_rolls_back(monkeypatch):
    cursor = SequenceCursor([[(2, "ready")], [(True, False)]])
    connection = Connection(cursor)
    bind(monkeypatch, connection)
    with pytest.raises(ValueError, match="media_transition_blocked"):
        repository.PostgresMediaLibraryRepository().transition_asset(
            site_id="site-a", asset_id=UUID(int=1), actor_ref="user:test",
            target="soft_deleted", expected_version=2, idempotency_key="delete-1",
        )
    assert connection.rollbacks == 1 and connection.commits == 0


def test_export_collection_job_and_retrieval_workflows_are_scoped(monkeypatch):
    now = datetime(2026, 9, 6, tzinfo=UTC)
    cursor = SequenceCursor([
        [(UUID(int=8), "queued", now)],
        [(UUID(int=9), "Launch", "private", [], 1, 2)],
        [],
        [(UUID(int=10),)],
        [(UUID(int=1),)],
        [],
        [(UUID(int=11), UUID(int=1), "inspect", "retryable", 1, 3, "media_scan_down", now, None, now)],
        [(UUID(int=1), "inspect", 1, 3)],
        [],
        [(UUID(int=8), "csv", "ready", "a" * 64, datetime(2099, 1, 1, tzinfo=UTC), "")],
    ])
    connection = Connection(cursor)
    bind(monkeypatch, connection)
    repo = repository.PostgresMediaLibraryRepository()
    export = repo.create_export(
        site_id="site-a", actor_ref="user:test", output_format="csv",
        projection=["id"], request_digest="a" * 64, expires_at=now,
    )
    collections = repo.list_collections(site_id="site-a", actor_ref="user:test", roles=[])
    created = repo.create_collection(
        site_id="site-a", actor_ref="user:test", title="Launch",
        visibility="private", shared_roles=[],
    )
    added = repo.add_collection_assets(
        site_id="site-a", actor_ref="user:test", roles=[], collection_id=UUID(int=10),
        asset_ids=[UUID(int=1)],
    )
    jobs = repo.list_jobs(site_id="site-a", asset_id=UUID(int=1), limit=10)
    retry = repo.retry_job(site_id="site-a", job_id=UUID(int=11), actor_ref="user:test")
    status = repo.get_export(site_id="site-a", export_id=UUID(int=8), actor_ref="user:test")
    assert export["status"] == "queued"
    assert collections["items"][0]["assetCount"] == 2
    assert created["title"] == "Launch" and added["added"] == 1
    assert jobs["items"][0]["errorCode"] == "media_scan_down"
    assert retry["status"] == "queued" and status["status"] == "ready"
    assert connection.commits == 4
