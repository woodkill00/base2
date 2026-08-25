from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.security.tenant_context import (
    TenantBoundaryError,
    TenantJobEnvelope,
    canonical_tenant_id,
    tenant_cache_key,
)


@pytest.mark.parametrize(
    "value",
    ["", "ab", "Tenant-A", "tenant_a", "../tenant", "tenant/a", "tenant a", "t" * 64],
)
def test_hostile_tenant_identifiers_fail_closed(value):
    with pytest.raises(TenantBoundaryError, match="tenant_invalid"):
        canonical_tenant_id(value)


def test_cache_and_job_namespaces_are_tenant_bound_and_collision_resistant():
    assert tenant_cache_key("search", "tenant-a", "result", "42") == (
        "search:tenant:tenant-a:result:42"
    )
    assert tenant_cache_key("search", "tenant-a", "result") != tenant_cache_key(
        "search", "tenant-b", "result"
    )
    envelope = TenantJobEnvelope.parse(
        {"tenant_id": "tenant-a", "job_id": "job-1", "operation": "search.reindex"}
    )
    assert envelope.as_dict()["tenant_id"] == "tenant-a"
    with pytest.raises(TenantBoundaryError, match="job_envelope_invalid"):
        TenantJobEnvelope.parse(
            {
                "tenant_id": "tenant-a",
                "job_id": "job-1",
                "operation": "search.reindex",
                "command": "ignored-but-hostile",
            }
        )


@pytest.mark.parametrize(
    ("value", "error"),
    [
        ({"tenant_id": "tenant-a", "job_id": "bad/id", "operation": "index"}, "job_id_invalid"),
        (
            {"tenant_id": "tenant-a", "job_id": "job-1", "operation": "bad operation"},
            "job_operation_invalid",
        ),
    ],
)
def test_job_envelope_rejects_unsafe_identifiers(value, error):
    with pytest.raises(TenantBoundaryError, match=error):
        TenantJobEnvelope.parse(value)


def test_cache_namespace_and_parts_reject_ambiguous_values():
    with pytest.raises(TenantBoundaryError, match="cache_namespace_invalid"):
        tenant_cache_key("bad namespace", "tenant-a", "safe")
    with pytest.raises(TenantBoundaryError, match="cache_key_part_invalid"):
        tenant_cache_key("search", "tenant-a", "../escape")


def test_invalid_request_tenant_is_rejected_before_route_work():
    response = TestClient(app).get("/api/content", headers={"X-Tenant-Id": "../tenant"})
    assert response.status_code == 400
    assert response.json() == {"detail": "tenant_invalid"}


class _Cursor:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))


class _Connection:
    closed = 0

    def __init__(self):
        self.calls = []
        self.rollbacks = 0
        self.resets = 0

    def cursor(self):
        return _Cursor(self.calls)

    def rollback(self):
        self.rollbacks += 1

    def reset(self):
        self.resets += 1


class _Pool:
    def __init__(self, conn):
        self.conn = conn
        self.returned = []

    def getconn(self):
        return self.conn

    def putconn(self, conn, close=False):
        self.returned.append((conn, close))


def test_pool_checkout_binds_exact_tenant_and_resets_on_return(monkeypatch):
    from api import db

    conn = _Connection()
    pool = _Pool(conn)
    monkeypatch.setattr(db, "_pool", pool)
    with db.db_conn(tenant_id="tenant-a") as checked_out:
        assert checked_out is conn
    assert conn.calls == [
        ("SELECT set_config('app.tenant_id', %s, true)", ("tenant-a",))
    ]
    assert conn.rollbacks == 1
    assert conn.resets == 1
    assert pool.returned == [(conn, False)]


def test_pool_checkout_resets_after_exception(monkeypatch):
    from api import db

    conn = _Connection()
    pool = _Pool(conn)
    monkeypatch.setattr(db, "_pool", pool)
    with pytest.raises(RuntimeError, match="boom"), db.db_conn(tenant_id="tenant-a"):
        raise RuntimeError("boom")
    assert conn.rollbacks == conn.resets == 1
    assert pool.returned == [(conn, False)]


def test_every_site_content_query_has_explicit_tenant_predicate_and_context():
    source = (Path(__file__).parents[2] / "repositories" / "site_content.py").read_text()
    assert source.count("db_conn(tenant_id=site_id)") == 6
    assert source.count("site_id=%s") >= 5
    assert "(id,site_id,content_type" in source


def test_database_defense_status_cannot_claim_rls_before_role_separation():
    root = Path(__file__).parents[3]
    policy = json.loads((root / "shared/config/tenant-security.json").read_text())
    assert policy["applicationIsolation"] == {
        "cacheNamespaceRequired": True,
        "databaseContext": "transaction-local",
        "explicitRepositoryPredicateRequired": True,
        "jobEnvelopeRequired": True,
        "poolResetRequired": True,
    }
    rls = policy["postgresqlRls"]
    assert rls["status"] == "deferred"
    assert "dedicated-non-owner-runtime-role" in rls["activationRequirements"]
    assert "pool-reuse-reset-matrix" in rls["activationRequirements"]


def test_tenant_rate_limit_uses_private_tenant_namespace(monkeypatch):
    from api.security import rate_limit

    calls = []

    class Pipeline:
        def incr(self, key, amount):
            calls.append(("incr", key, amount))

        def pexpire(self, key, duration):
            calls.append(("pexpire", key, duration))

        def execute(self):
            return [1, True]

    class Redis:
        def pipeline(self):
            return Pipeline()

    monkeypatch.setattr(rate_limit, "get_client", lambda: Redis())
    monkeypatch.setattr(rate_limit, "now_ms", lambda: 1_000)
    result = rate_limit.incr_and_check_tenant_detailed(
        "tenant-a", "2001:db8::1%private", "public_form"
    )
    assert result == (1, False, 0)
    key = calls[0][1]
    assert key.startswith("rate_limit:rate-limit:tenant:tenant-a:public_form:")
    assert "2001:db8" not in key
