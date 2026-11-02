"""Source contracts; actual PostgreSQL authority tests live in the disposable runner."""

from importlib import import_module
from types import SimpleNamespace


def module():
    return import_module("sitecontent.migrations.0039_review_history_retention_privacy")


def test_sqlite_is_noop():
    module().configure(None, SimpleNamespace(connection=SimpleNamespace(vendor="sqlite")))


def test_retention_authority_is_not_caller_selected():
    sql = module().SQL
    assert "base2_purge_review_history(p_site text,p_record uuid)" in sql
    assert "INTERVAL '30 days'" in sql
    assert "session_user<>'__WORKER__'" in sql
    assert "p_site IS DISTINCT FROM current_setting('app.tenant_id',true)" in sql
    assert "state='deleted'" in sql
    assert "FOR UPDATE" in sql
    assert "sitecontent_assetbinding" in sql and "sitecontent_contentrelationship" in sql
    assert "recovery_days" not in sql


def test_capability_is_exact_and_not_a_guc():
    sql = module().SQL
    for fence in (
        "pg_backend_pid()",
        "txid_current()",
        "old_row=p_old",
        "new_row IS NOT DISTINCT FROM p_new",
        "row_id=p_id",
        "action=p_action",
    ):
        assert fence in sql
    assert "REVOKE ALL ON public.base2_review_maintenance_capability FROM PUBLIC" in sql
    assert "set_config('app.review" not in sql


def test_claim_fences_and_authorization_invalidation():
    sql = module().SQL
    for fence in (
        "claim_token=requested_claim_token",
        "status='running'",
        "claim_expires_at>=NOW()",
        "retention_until>NOW()",
        "rights.kind<>requested_action",
        "session_user<>'__DATA__'",
    ):
        assert fence in sql
    assert "semantic_generation=r.semantic_generation+1" in sql
    assert "'semantic_revision',gen_random_uuid()" in sql
    assert "scheduled_by_id=NULL" in sql
    assert "submitter_id=NULL" in sql
    assert "base2_apply_data_rights_subject_action_legacy_0031" in sql
    assert "review_maintenance" in sql


def test_typed_surface_inventory_is_complete():
    fields = module().SUBJECT_COLUMNS
    assert fields["sitecontent_reviewsubject"] == (
        "original_creator_id",
        "semantic_author_id",
        "submitter_id",
        "scheduled_by_id",
    )
    assert fields["sitecontent_reviewapproval"] == ("reviewer_id",)
    for table in ("reviewdigestbatch", "reviewnotificationintent", "reviewnotificationdelivery"):
        assert fields["sitecontent_" + table] == ("recipient_id",)


def test_configure_revokes_legacy_entrypoints_and_only_grants_bounded_helpers(monkeypatch):
    from contextlib import nullcontext
    from unittest.mock import Mock

    migration = module()
    helper = import_module("sitecontent.migrations.0031_data_rights_worker_scope")
    monkeypatch.setattr(helper, "_role", lambda editor, var: (var.lower(), '"' + var.lower() + '"'))
    cur = Mock()
    cur.fetchone.return_value = (True,)
    editor = SimpleNamespace(
        connection=SimpleNamespace(vendor="postgresql", cursor=lambda: nullcontext(cur))
    )
    migration.configure(None, editor)
    statements = [call.args[0] for call in cur.execute.call_args_list]
    for signature in migration.SIGNATURES:
        assert any(
            line.startswith("REVOKE ALL ON FUNCTION public." + signature) for line in statements
        )
    grants = [line for line in statements if line.startswith("GRANT")]
    assert len(grants) == 3
    assert not any("legacy_0031" in line or "maintenance_allowed" in line for line in grants)
    assert not any("GRANT DELETE" in line or "GRANT UPDATE" in line for line in grants)


def test_postgres_reverse_fails_closed():
    import pytest

    with pytest.raises(RuntimeError, match="rollback_requires"):
        module().reverse(None, SimpleNamespace(connection=SimpleNamespace(vendor="postgresql")))


def test_subject_projection_retains_correction_and_deletion_compatibility():
    sql = module().SQL
    assert "AND kind IN ('export','correction','deletion')" in sql
    assert "PERFORM set_config('app.tenant_id',rights.tenant_id,true)" in sql
    assert "rights.tenant_id IS DISTINCT FROM current_setting" not in sql
