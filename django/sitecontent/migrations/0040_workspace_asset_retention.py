"""Freeze legacy local purge ownership before irreversible filesystem IO.

Reuses MediaPurgePlan and MediaAsset's planned/purged states. Private proof is
execution authority, not a second domain model: runtime callers cannot forge it.
Rollback requires an operator plan because committed purge intent is irreversible.

Nonsemantic parent reassignment must lock old/new parents in UUID order before
prelocking reference rows. No dedicated parent-reassignment API is introduced.
Arbitrary external raw/ORM prelocks may deadlock/abort; no deadlock-free claim is made.
Unchanged-parent bookkeeping has a no-parent-lock fast path while no proof exists.

Completion scrubs only the four asset user fields. Exact keys, hashes, sizes,
versions, timestamps, proof, plan and scoped audit remain as retention evidence;
this is not general personal-data erasure. Governed metadata histories block claim.
"""

from importlib import import_module

from django.db import migrations

SQL = r"""
CREATE TABLE public.base2_workspace_purge_proof (
 plan_id uuid PRIMARY KEY REFERENCES public.sitecontent_mediapurgeplan(id),
 asset_id uuid NOT NULL UNIQUE REFERENCES public.sitecontent_mediaasset(id),
 organization_id uuid NOT NULL
);
CREATE TABLE public.base2_workspace_purge_capability (
 backend_pid integer NOT NULL, transaction_id bigint NOT NULL,
 asset_id uuid NOT NULL, operation text NOT NULL CHECK(operation IN ('claim','complete')),
 PRIMARY KEY(backend_pid,transaction_id,asset_id)
);
REVOKE ALL ON public.base2_workspace_purge_proof,public.base2_workspace_purge_capability FROM
  PUBLIC;

CREATE FUNCTION public.base2_workspace_purge_guard()
RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE old_data jsonb:=CASE WHEN TG_OP='INSERT' THEN NULL ELSE to_jsonb(OLD) END;
 new_data jsonb:=CASE WHEN TG_OP='DELETE' THEN NULL ELSE to_jsonb(NEW) END;
 asset uuid; op text; protected boolean; parent_status text;
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' THEN
   RAISE EXCEPTION 'content_retention_isolation_unsupported' USING ERRCODE='25000'; END IF;
 -- A proof-bound plan may be updated only by its exact completion capability.
 -- Reject native plan writers before acquiring its parent to avoid plan/asset inversion.
 IF TG_TABLE_NAME='sitecontent_mediapurgeplan' AND TG_OP IN ('UPDATE','DELETE') THEN
   SELECT p.asset_id INTO asset FROM public.base2_workspace_purge_proof p
     WHERE p.plan_id=(old_data->>'id')::uuid;
   IF FOUND AND NOT EXISTS(SELECT 1 FROM public.base2_workspace_purge_capability c
     WHERE c.backend_pid=pg_backend_pid() AND c.transaction_id=txid_current()
       AND c.asset_id=asset AND c.operation='complete') THEN
     RAISE EXCEPTION 'content_retention_intent_immutable' USING ERRCODE='23514'; END IF;
 END IF;
 -- Unchanged-parent bookkeeping cannot introduce a dependency: an existing row
 -- already blocks claim. Avoid adding job-row -> asset-row locks to such updates.
 IF TG_TABLE_NAME IN ('sitecontent_mediareference','sitecontent_mediaretentionhold',
   'sitecontent_mediapurgeplan','sitecontent_mediacollectionmembership','sitecontent_mediajob',
   'sitecontent_mediadeliverygrant','sitecontent_mediaabusecase',
   'sitecontent_mediauploadsession','sitecontent_mediametadatarevision') AND
   TG_OP IN ('UPDATE','DELETE') AND
   (TG_OP='DELETE' OR
     (new_data->>CASE WHEN TG_TABLE_NAME='sitecontent_mediauploadsession' THEN 'asset_ref'
       ELSE 'asset_id' END) IS NOT DISTINCT FROM
     (old_data->>CASE WHEN TG_TABLE_NAME='sitecontent_mediauploadsession' THEN 'asset_ref'
       ELSE 'asset_id' END)) AND NOT EXISTS(
       SELECT 1 FROM public.base2_workspace_purge_proof p WHERE p.asset_id=
         (old_data->>CASE WHEN TG_TABLE_NAME='sitecontent_mediauploadsession' THEN 'asset_ref'
           ELSE 'asset_id' END)::uuid) THEN
   IF TG_OP='DELETE' THEN RETURN OLD; END IF;
   RETURN NEW;
 END IF;
 -- Only the trusted migration owner may preserve imported historical clocks.
 -- Supported runtime sessions cannot make a freshly deleted asset appear older.
 IF TG_TABLE_NAME='sitecontent_mediaasset' AND TG_OP IN ('INSERT','UPDATE') AND
    session_user<>current_user THEN
   IF NEW.status='deleted' THEN
     IF TG_OP='INSERT' OR OLD.status IS DISTINCT FROM 'deleted' THEN
       NEW.deleted_at:=clock_timestamp();
     ELSIF NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
       RAISE EXCEPTION 'content_retention_deletion_clock_immutable' USING ERRCODE='23514';
     END IF;
     IF TG_OP='UPDATE' AND OLD.status='deleted' AND OLD.retention_until IS NOT NULL AND
       (NEW.retention_until IS NULL OR NEW.retention_until<OLD.retention_until) THEN
       RAISE EXCEPTION 'content_retention_schedule_cannot_shorten' USING ERRCODE='23514';
     END IF;
   END IF;
   new_data:=to_jsonb(NEW);
 END IF;
 asset:=COALESCE(new_data,old_data)->>CASE WHEN TG_TABLE_NAME='sitecontent_mediaasset'
   THEN 'id' WHEN TG_TABLE_NAME='sitecontent_mediauploadsession' THEN 'asset_ref'
   ELSE 'asset_id' END;
 -- The explicit loop also fences changing a variant/reference away from a frozen parent.
 FOR asset IN SELECT DISTINCT x FROM unnest(ARRAY[asset,
   (old_data->>CASE WHEN TG_TABLE_NAME='sitecontent_mediaasset' THEN 'id'
     WHEN TG_TABLE_NAME='sitecontent_mediauploadsession' THEN 'asset_ref'
     ELSE 'asset_id' END)::uuid]) x WHERE x IS NOT NULL ORDER BY x
 LOOP
   -- Parent-before-reference protocol: claim takes FOR UPDATE; reference writers
   -- take KEY SHARE before a separate fresh READ COMMITTED status/proof check.
   SELECT status INTO parent_status FROM public.sitecontent_mediaasset
     WHERE id=asset FOR KEY SHARE;
   IF parent_status IN ('purge_planned','purged') AND
      TG_TABLE_NAME NOT IN ('sitecontent_mediaasset','sitecontent_mediapurgeplan') THEN
     RAISE EXCEPTION 'content_retention_intent_immutable' USING ERRCODE='23514'; END IF;
   SELECT EXISTS(SELECT 1 FROM public.base2_workspace_purge_proof p WHERE p.asset_id=asset)
     INTO protected;
   IF NOT protected THEN CONTINUE; END IF;
   SELECT c.operation INTO op FROM public.base2_workspace_purge_capability c
     WHERE c.backend_pid=pg_backend_pid() AND c.transaction_id=txid_current() AND c.asset_id=asset;
   IF TG_TABLE_NAME='sitecontent_mediaasset' AND TG_OP='UPDATE' AND
      (new_data->>'lock_version')::bigint=(old_data->>'lock_version')::bigint+1 AND
      (new_data->>'authorization_epoch')::bigint=(old_data->>'authorization_epoch')::bigint+1 THEN
     IF op='claim' AND old_data->>'status'='deleted' AND new_data->>'status'='purge_planned' AND
        (new_data-ARRAY['status','lock_version','authorization_epoch','updated_at'])=
        (old_data-ARRAY['status','lock_version','authorization_epoch','updated_at']) THEN
       CONTINUE;
     END IF;
     IF op='complete' AND old_data->>'status'='purge_planned' AND new_data->>'status'='purged' AND
        (new_data-ARRAY['status','lock_version','authorization_epoch','updated_at',
          'original_name','owner_ref','attribution','metadata'])=
        (old_data-ARRAY['status','lock_version','authorization_epoch','updated_at',
          'original_name','owner_ref','attribution','metadata']) AND
        new_data->>'original_name'='purged' AND new_data->>'owner_ref'='system:retention' AND
        new_data->>'attribution'='' AND new_data->'metadata'='{}'::jsonb THEN
       CONTINUE;
     END IF;
   END IF;
   IF TG_TABLE_NAME='sitecontent_mediapurgeplan' AND TG_OP='UPDATE' AND op='complete' AND
      (new_data-ARRAY['status','completed_at','result_sha256','updated_at'])=
      (old_data-ARRAY['status','completed_at','result_sha256','updated_at']) AND
      old_data->>'status'='scheduled' AND new_data->>'status'='completed' AND
      new_data->>'completed_at' IS NOT NULL AND new_data->>'result_sha256' ~ '^[a-f0-9]{64}$' THEN
     CONTINUE;
   END IF;
   RAISE EXCEPTION 'content_retention_intent_immutable' USING ERRCODE='23514';
 END LOOP;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.base2_claim_workspace_asset_purge(p_site text,p_asset uuid)
RETURNS TABLE(plan_id uuid,object_manifest jsonb) LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE a public.sitecontent_mediaasset; v record; objects jsonb:='[]'::jsonb;
 claimed uuid; object_id text; existing record; org uuid;
BEGIN
 IF session_user<>'__WORKER__' OR p_site IS DISTINCT FROM current_setting('app.tenant_id',true)
   THEN RAISE EXCEPTION 'content_retention_role_required' USING ERRCODE='42501'; END IF;
 IF current_setting('transaction_isolation')<>'read committed' THEN
   RAISE EXCEPTION 'content_retention_isolation_unsupported' USING ERRCODE='25000'; END IF;
 PERFORM pg_advisory_xact_lock(hashtext('base2-workspace-policy-v1'));
 SELECT * INTO a FROM public.sitecontent_mediaasset WHERE id=p_asset AND site_id=p_site FOR UPDATE;
 IF NOT FOUND THEN RETURN; END IF;
 SELECT p.id,p.object_manifest,p.status INTO existing FROM public.base2_workspace_purge_proof proof
   JOIN public.sitecontent_mediapurgeplan p ON p.id=proof.plan_id
   WHERE proof.asset_id=p_asset AND p.site_id=p_site;
 IF FOUND THEN
   IF existing.status='scheduled' AND a.status='purge_planned' THEN
     RETURN QUERY SELECT existing.id,existing.object_manifest;
   END IF;
   RETURN;
 END IF;
 SELECT id INTO org FROM public.api_identity_organizations WHERE tenant_id=p_site;
 IF org IS NULL THEN RAISE EXCEPTION 'content_retention_organization_unavailable' USING
  ERRCODE='23514'; END IF;
 IF a.status<>'deleted' OR a.retention_until IS NULL OR a.retention_until>NOW() THEN RETURN; END IF;
 IF a.deleted_at IS NULL THEN RAISE EXCEPTION 'content_retention_recovery_evidence_missing'
  USING ERRCODE='23514'; END IF;
 IF a.deleted_at>NOW()-INTERVAL '30 days' THEN RETURN; END IF;
 IF EXISTS(SELECT 1 FROM public.sitecontent_assetbinding WHERE asset_id=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediareference WHERE asset_id=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediaretentionhold WHERE asset_id=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediacollectionmembership WHERE asset_id=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediajob WHERE asset_id=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediadeliverygrant WHERE asset_id=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediaabusecase WHERE asset_id=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediauploadsession WHERE asset_ref=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediapurgeplan WHERE asset_id=p_asset)
    THEN RETURN; END IF;
 -- Unsupported remote/governed keys never acquire a destructive intent.
 IF EXISTS(SELECT 1 FROM public.sitecontent_mediaobjectversion WHERE asset_id=p_asset) OR
    EXISTS(SELECT 1 FROM public.sitecontent_mediametadatarevision WHERE asset_id=p_asset) THEN
   RAISE EXCEPTION 'content_retention_storage_unsupported' USING ERRCODE='23514'; END IF;
 IF a.storage_key IS DISTINCT FROM 'media/'||p_site||'/'||p_asset::text||'.bin' OR
    a.sha256 !~ '^[a-f0-9]{64}$' OR a.byte_size NOT BETWEEN 1 AND 104857600 THEN
   RAISE EXCEPTION 'content_retention_storage_unsupported' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM public.sitecontent_mediavariant WHERE asset_id=p_asset)>127 OR
    (SELECT count(*)<>count(DISTINCT storage_key) FROM public.sitecontent_mediavariant
      WHERE asset_id=p_asset) THEN
   RAISE EXCEPTION 'content_retention_manifest_invalid' USING ERRCODE='23514'; END IF;
 FOR v IN SELECT * FROM public.sitecontent_mediavariant WHERE asset_id=p_asset ORDER BY name,id
 LOOP
   IF v.name !~ '^[a-zA-Z0-9_-]{1,64}$' OR v.sha256 !~ '^[a-f0-9]{64}$' OR
      v.byte_size NOT BETWEEN 1 AND 104857600 THEN
     RAISE EXCEPTION 'content_retention_manifest_invalid' USING ERRCODE='23514'; END IF;
   IF v.storage_key='variants/'||p_site||'/'||p_asset::text||'-'||v.name||'.bin' THEN
     object_id:=p_asset::text||'-'||v.name;
   ELSIF
  v.storage_key='variants/'||p_site||'/'||p_asset::text||'-v'||a.current_object_version::text||'-'||v.name||'.bin'
  THEN
     object_id:=p_asset::text||'-v'||a.current_object_version::text||'-'||v.name;
   ELSE RAISE EXCEPTION 'content_retention_storage_unsupported' USING ERRCODE='23514'; END IF;
objects:=objects||jsonb_build_array(jsonb_build_object('namespace','variants','object_id',object_id,
     'object_key',v.storage_key,'sha256',v.sha256,'byte_size',v.byte_size));
 END LOOP;
objects:=objects||jsonb_build_array(jsonb_build_object('namespace','media','object_id',p_asset::text,
   'object_key',a.storage_key,'sha256',a.sha256,'byte_size',a.byte_size));
 claimed:=gen_random_uuid();
 INSERT INTO public.sitecontent_mediapurgeplan
   (id,site_id,asset_id,requested_by,reason_code,expected_version,object_manifest,reference_preview,
    status,scheduled_at,completed_at,result_sha256,created_at,updated_at)
VALUES(claimed,p_site,p_asset,'system:retention','workspace_retention',a.lock_version,objects,'[]'::jsonb,
   'scheduled',NOW(),NULL,'',NOW(),NOW());
 INSERT INTO public.base2_workspace_purge_proof VALUES(claimed,p_asset,org);
 INSERT INTO public.base2_workspace_purge_capability
  VALUES(pg_backend_pid(),txid_current(),p_asset,'claim');
 UPDATE public.sitecontent_mediaasset SET status='purge_planned',lock_version=lock_version+1,
   authorization_epoch=authorization_epoch+1,updated_at=NOW() WHERE id=p_asset;
 DELETE FROM public.base2_workspace_purge_capability WHERE backend_pid=pg_backend_pid()
   AND transaction_id=txid_current() AND asset_id=p_asset;
 RETURN QUERY SELECT claimed,objects;
END $$;

CREATE FUNCTION public.base2_complete_workspace_asset_purge(p_site text,p_plan uuid,p_result text)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE asset uuid; org uuid; p public.sitecontent_mediapurgeplan;
BEGIN
 IF session_user<>'__WORKER__' OR p_site IS DISTINCT FROM current_setting('app.tenant_id',true)
   THEN RAISE EXCEPTION 'content_retention_role_required' USING ERRCODE='42501'; END IF;
 IF p_result IS NULL OR p_result !~ '^[a-f0-9]{64}$' THEN
   RAISE EXCEPTION 'content_integrity_failed' USING ERRCODE='23514'; END IF;
 IF current_setting('transaction_isolation')<>'read committed' THEN
   RAISE EXCEPTION 'content_retention_isolation_unsupported' USING ERRCODE='25000'; END IF;
 PERFORM pg_advisory_xact_lock(hashtext('base2-workspace-policy-v1'));
 SELECT proof.asset_id,proof.organization_id INTO asset,org
 FROM public.base2_workspace_purge_proof proof WHERE proof.plan_id=p_plan;
 IF NOT FOUND THEN RAISE EXCEPTION 'content_retention_plan_invalid' USING ERRCODE='23514'; END IF;
 PERFORM 1 FROM public.sitecontent_mediaasset WHERE id=asset AND site_id=p_site FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'content_retention_plan_invalid' USING ERRCODE='23514'; END IF;
 SELECT * INTO p FROM public.sitecontent_mediapurgeplan WHERE id=p_plan AND site_id=p_site FOR
  UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'content_retention_plan_invalid' USING ERRCODE='23514'; END IF;
 IF p.status='completed' THEN
   IF p.result_sha256<>p_result THEN RAISE EXCEPTION 'content_integrity_failed' USING
  ERRCODE='23514'; END IF;
   RETURN false;
 END IF;
 IF p.status<>'scheduled' THEN RAISE EXCEPTION 'content_retention_plan_invalid' USING
  ERRCODE='23514'; END IF;
 INSERT INTO public.base2_workspace_purge_capability
  VALUES(pg_backend_pid(),txid_current(),asset,'complete');
 UPDATE public.sitecontent_mediaasset SET status='purged',lock_version=lock_version+1,
   original_name='purged',owner_ref='system:retention',attribution='',metadata='{}'::jsonb,
   authorization_epoch=authorization_epoch+1,updated_at=NOW() WHERE id=asset;
 UPDATE public.sitecontent_mediapurgeplan SET
  status='completed',completed_at=NOW(),result_sha256=p_result,
   updated_at=NOW() WHERE id=p_plan;
 INSERT INTO public.sitecontent_workspaceauditevent
   (id,site_id,actor_ref,object_type,object_ref,action,outcome,correlation_id,metadata,created_at)
 VALUES(gen_random_uuid(),p_site,'system:retention','media_asset',asset::text,
   'content.asset_hard_delete','accepted','','{"count":1}'::jsonb,NOW());
 INSERT INTO public.api_auth_audit_events(id,user_id,action,ip,user_agent,metadata_json)
 VALUES(gen_random_uuid(),NULL,'content.asset_hard_delete','','',jsonb_build_object(
   'tenant_id',p_site,'organization_id',org,'asset_id',asset,'count',1,
   'actor_ref','system:retention'));
 DELETE FROM public.base2_workspace_purge_capability WHERE backend_pid=pg_backend_pid()
   AND transaction_id=txid_current() AND asset_id=asset;
 RETURN true;
END $$;
"""

SIGNATURES = (
    "base2_workspace_purge_guard()",
    "base2_claim_workspace_asset_purge(text,uuid)",
    "base2_complete_workspace_asset_purge(text,uuid,text)",
)
GUARDED = (
    "sitecontent_mediaasset",
    "sitecontent_mediavariant",
    "sitecontent_mediaobjectversion",
    "sitecontent_assetbinding",
    "sitecontent_mediareference",
    "sitecontent_mediaretentionhold",
    "sitecontent_mediapurgeplan",
    "sitecontent_mediacollectionmembership",
    "sitecontent_mediajob",
    "sitecontent_mediadeliverygrant",
    "sitecontent_mediaabusecase",
    "sitecontent_mediauploadsession",
    "sitecontent_mediametadatarevision",
)
# Nonsemantic tables use only the parent KEY SHARE protocol, not a new global lock.
PARENT_LOCKED = (
    "sitecontent_mediareference",
    "sitecontent_mediaretentionhold",
    "sitecontent_mediapurgeplan",
    "sitecontent_mediacollectionmembership",
    "sitecontent_mediajob",
    "sitecontent_mediadeliverygrant",
    "sitecontent_mediaabusecase",
    "sitecontent_mediauploadsession",
    "sitecontent_mediametadatarevision",
)


def configure(apps, editor):
    del apps
    if editor.connection.vendor != "postgresql":
        return
    helper = import_module("sitecontent.migrations.0031_data_rights_worker_scope")
    worker, quoted_worker = helper._role(editor, "WORKSPACE_WORKER_DB_USER")
    roles = [quoted_worker]
    for variable in (
        "WORKSPACE_DB_USER",
        "API_RUNTIME_DB_USER",
        "RUNTIME_WORKER_DB_USER",
        "DATA_RIGHTS_WORKER_DB_USER",
        "EMAIL_WORKER_DB_USER",
    ):
        roles.append(helper._role(editor, variable)[1])
    with editor.connection.cursor() as cur:
        cur.execute("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")
        if not cur.fetchone()[0]:
            raise RuntimeError("workspace_retention:migration_owner_rls_capability_required")
        cur.execute(SQL.replace("__WORKER__", worker.replace("'", "''")))
        cur.execute(
            "REVOKE ALL ON public.base2_workspace_purge_proof,"
            "public.base2_workspace_purge_capability FROM " + ",".join(roles)
        )
        for signature in SIGNATURES:
            cur.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC," + ",".join(roles))
        for signature in SIGNATURES[1:]:
            cur.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {quoted_worker}")
        for table in GUARDED:
            cur.execute(
                "CREATE TRIGGER workspace_purge_guard BEFORE INSERT OR UPDATE OR DELETE "
                f"ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_purge_guard()"
            )


def reverse(apps, editor):
    if editor.connection.vendor == "postgresql":
        raise RuntimeError(
            "workspace_retention:rollback_requires_enforcing_source_and_operator_plan"
        )


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0039_review_history_retention_privacy")]
    operations = [migrations.RunPython(configure, reverse)]
