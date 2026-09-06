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
