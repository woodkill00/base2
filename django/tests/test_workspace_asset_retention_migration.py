"""Source contracts only; restricted-role/concurrency proof runs against PostgreSQL."""

from contextlib import nullcontext
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def migration():
    return import_module("sitecontent.migrations.0040_workspace_asset_retention")


def test_no_new_canonical_model_and_sqlite_noop():
    migration().configure(None, SimpleNamespace(connection=SimpleNamespace(vendor="sqlite")))
    assert "sitecontent_mediapurgeplan" in migration().SQL
    assert "CREATE TABLE public.sitecontent_" not in migration().SQL


def test_worker_only_claim_binds_private_proof_not_mutable_status_or_guc():
    sql = migration().SQL
    assert sql.count("session_user<>'__WORKER__'") == 2
    assert sql.count("p_site IS DISTINCT FROM current_setting('app.tenant_id',true)") == 2
    assert "INSERT INTO public.base2_workspace_purge_proof VALUES(claimed,p_asset,org)" in sql
    assert "pg_backend_pid()" in sql and "txid_current()" in sql
    assert "set_config('app." not in sql
    assert (
        "REVOKE ALL ON public.base2_workspace_purge_proof,"
        "public.base2_workspace_purge_capability FROM PUBLIC" in " ".join(sql.split())
    )


def test_recovery_floor_and_exact_local_objects_checked_before_claim():
    sql = migration().SQL
    before, after = sql.split("INSERT INTO public.sitecontent_mediapurgeplan", 1)
    for fragment in (
        "a.status<>'deleted'",
        "a.retention_until>NOW()",
        "INTERVAL '30 days'",
        "content_retention_recovery_evidence_missing",
        "content_retention_storage_unsupported",
        "sitecontent_assetbinding",
        "sitecontent_mediareference",
        "sitecontent_mediaretentionhold",
        "sitecontent_mediaobjectversion",
        "count(*)",
        ">127",
        "104857600",
    ):
        assert fragment in before
    assert "'scheduled'" in after
    assert "DELETE FROM public.sitecontent_mediaasset" not in sql


def test_lock_precedes_parent_and_retry_reuses_manifest():
    sql = migration().SQL
    claim = sql.split("CREATE FUNCTION public.base2_claim_workspace_asset_purge", 1)[1]
    assert claim.index(
        "pg_advisory_xact_lock(hashtext('base2-workspace-policy-v1'))"
    ) < claim.index("FROM public.sitecontent_mediaasset")
    assert "RETURN QUERY SELECT existing.id,existing.object_manifest" in claim
    assert "IF p.status='completed'" in sql and "RETURN false" in sql


def test_guard_covers_old_and_new_parent_and_exact_capability_updates():
    sql = migration().SQL
    assert "(old_data->>CASE WHEN TG_TABLE_NAME=" in sql
    assert "ELSE 'asset_id' END)::uuid" in sql
    assert "new_data-ARRAY['status','lock_version','authorization_epoch','updated_at']" in sql
    assert "op='claim'" in sql and "op='complete'" in sql
    for table in (
        "sitecontent_mediaasset",
        "sitecontent_mediavariant",
        "sitecontent_assetbinding",
        "sitecontent_mediareference",
        "sitecontent_mediaretentionhold",
        "sitecontent_mediaobjectversion",
        "sitecontent_mediapurgeplan",
    ):
        assert table in migration().GUARDED


def test_configure_revokes_all_runtime_roles_and_grants_only_two_worker_functions(monkeypatch):
    helper = import_module("sitecontent.migrations.0031_data_rights_worker_scope")
    monkeypatch.setattr(helper, "_role", lambda editor, var: (var.lower(), '"' + var.lower() + '"'))
    cur = Mock()
    cur.fetchone.return_value = (True,)
    editor = SimpleNamespace(
        connection=SimpleNamespace(vendor="postgresql", cursor=lambda: nullcontext(cur))
    )
    migration().configure(None, editor)
    statements = [call.args[0] for call in cur.execute.call_args_list]
    grants = [s for s in statements if s.startswith("GRANT")]
    assert len(grants) == 2
    assert all('TO "workspace_worker_db_user"' in s for s in grants)
    assert not any(
        "GRANT DELETE" in s or "GRANT UPDATE" in s or "purge_guard() TO" in s for s in grants
    )
    assert sum("CREATE TRIGGER workspace_purge_guard" in s for s in statements) == len(
        migration().GUARDED
    )


def test_reverse_requires_operator_plan():
    with pytest.raises(RuntimeError, match="rollback_requires"):
        migration().reverse(None, SimpleNamespace(connection=SimpleNamespace(vendor="postgresql")))


def test_scoped_audit_uses_immutable_server_captured_organization():
    sql = migration().SQL
    assert "SELECT id INTO org FROM public.api_identity_organizations WHERE tenant_id=p_site" in sql
    assert "content_retention_organization_unavailable" in sql
    assert "INSERT INTO public.base2_workspace_purge_proof VALUES(claimed,p_asset,org)" in sql
    finalize = sql.split("CREATE FUNCTION public.base2_complete_workspace_asset_purge", 1)[1]
    assert "proof.organization_id INTO asset,org" in finalize
    assert "FROM public.api_identity_organizations" not in finalize
    assert "NULL,'content.asset_hard_delete'" in finalize
    assert "'tenant_id',p_site,'organization_id',org,'asset_id',asset,'count',1" in finalize


def test_runtime_deletion_clock_is_server_owned_without_rewriting_legacy_history():
    sql = migration().SQL
    assert "session_user<>current_user" in sql
    assert "OLD.status IS DISTINCT FROM 'deleted'" in sql
    assert "NEW.deleted_at:=clock_timestamp()" in sql
    assert "NEW.deleted_at IS DISTINCT FROM OLD.deleted_at" in sql
    assert "content_retention_deletion_clock_immutable" in sql
    assert "NEW.retention_until<OLD.retention_until" in sql
    assert "content_retention_schedule_cannot_shorten" in sql
    assert "UPDATE public.sitecontent_mediaasset SET deleted_at" not in sql


def test_reference_protocol_uses_sorted_parent_locks_not_extra_global_triggers():
    sql = migration().SQL
    assert "x WHERE x IS NOT NULL ORDER BY x" in sql
    assert "WHERE id=asset FOR KEY SHARE" in sql
    assert "parent_status IN ('purge_planned','purged')" in sql
    assert sql.count("current_setting('transaction_isolation')<>'read committed'") == 3
    assert "sitecontent_mediametadatarevision" in migration().PARENT_LOCKED
    assert len(migration().PARENT_LOCKED) == 9


def test_completion_scrubs_only_authorized_user_fields_and_preserves_execution_manifest():
    sql = migration().SQL
    assert (
        "original_name='purged',owner_ref='system:retention',attribution='',metadata='{}'::jsonb"
        in sql
    )
    assert "new_data->>'original_name'='purged'" in sql
    assert "new_data->>'owner_ref'='system:retention'" in sql
    assert "new_data->>'attribution'='' AND new_data->'metadata'='{}'::jsonb" in sql
    assert (
        "EXISTS(SELECT 1 FROM public.sitecontent_mediametadatarevision WHERE asset_id=p_asset)"
        in sql
    )
    assert "DELETE FROM public.sitecontent_mediametadatarevision" not in sql


def test_bookkeeping_fast_path_and_plan_guard_avoid_reference_lock_inversions():
    sql = migration().SQL
    early = sql.split(" -- Only the trusted migration owner", 1)[0]
    assert "p.plan_id=(old_data->>'id')::uuid" in early
    assert "c.asset_id=asset AND c.operation='complete'" in early
    assert "TG_OP IN ('UPDATE','DELETE')" in early
    assert "IS NOT DISTINCT FROM" in early
    assert "NOT EXISTS(" in early
    for table in migration().PARENT_LOCKED:
        assert table in early
    assert "FOR UPDATE OF p" not in sql
    variant_loop = sql.split("FOR v IN SELECT", 1)[1].split("LOOP", 1)[0]
    assert "FOR UPDATE" not in variant_loop
