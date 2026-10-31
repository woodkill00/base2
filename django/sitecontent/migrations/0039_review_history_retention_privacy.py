"""Claim-fenced privacy and fixed-policy retention for typed review history.

The private capability relation is enforcement infrastructure, not domain state.
It is populated only inside these fixed SQL functions and consumed by the 0038
trigger seam; runtime roles receive neither relation access nor callback EXECUTE.
Supported record recovery policy is fixed 30 days (content-workspace-operations).
"""
import importlib
from django.db import migrations

SUBJECT_COLUMNS = {
    'sitecontent_reviewsubject': ('original_creator_id', 'semantic_author_id', 'submitter_id', 'scheduled_by_id'),
    'sitecontent_reviewapproval': ('reviewer_id',),
    'sitecontent_reviewdigestbatch': ('recipient_id',),
    'sitecontent_reviewnotificationintent': ('recipient_id',),
    'sitecontent_reviewnotificationdelivery': ('recipient_id',),
}

SQL = r"""
CREATE TABLE public.base2_review_maintenance_capability (
 backend integer NOT NULL, transaction_id bigint NOT NULL, table_name text NOT NULL,
 row_id uuid NOT NULL, action text NOT NULL CHECK(action IN ('UPDATE','DELETE')),
 old_row jsonb NOT NULL, new_row jsonb,
 PRIMARY KEY(backend,transaction_id,table_name,row_id,action)
);
REVOKE ALL ON public.base2_review_maintenance_capability FROM PUBLIC;
CREATE OR REPLACE FUNCTION public.base2_review_maintenance_allowed(
 p_table text,p_id uuid,p_action text,p_old jsonb,p_new jsonb)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
BEGIN
 DELETE FROM public.base2_review_maintenance_capability
 WHERE backend=pg_backend_pid() AND transaction_id=txid_current()
 AND table_name=p_table AND row_id=p_id AND action=p_action
 AND old_row=p_old AND new_row IS NOT DISTINCT FROM p_new;
 RETURN FOUND;
END $$;
CREATE FUNCTION public.base2_purge_review_history(p_site text,p_record uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE approvals integer; intents integer; deliveries integer; subjects integer;
BEGIN
 IF session_user<>'__WORKER__' OR p_site IS DISTINCT FROM current_setting('app.tenant_id',true) THEN
  RAISE EXCEPTION 'review_retention_authority_required'; END IF;
 PERFORM pg_advisory_xact_lock(hashtext('base2-workspace-policy-v1'));
 PERFORM 1 FROM public.sitecontent_contentrecord WHERE id=p_record AND site_id=p_site
 AND state='deleted' AND deleted_at<=NOW()-INTERVAL '30 days' FOR UPDATE;
 IF NOT FOUND OR EXISTS(SELECT 1 FROM public.sitecontent_assetbinding WHERE record_id=p_record)
 OR EXISTS(SELECT 1 FROM public.sitecontent_contentrelationship WHERE source_id=p_record OR target_id=p_record) THEN
  RAISE EXCEPTION 'review_retention_not_eligible'; END IF;
 DELETE FROM public.sitecontent_reviewnotificationdelivery d USING public.sitecontent_reviewnotificationintent i
 WHERE d.intent_id=i.id AND i.record_id=p_record AND i.site_id=p_site AND d.site_id=p_site;
 GET DIAGNOSTICS deliveries=ROW_COUNT;
 DELETE FROM public.sitecontent_reviewnotificationintent WHERE record_id=p_record AND site_id=p_site;
 GET DIAGNOSTICS intents=ROW_COUNT;
 INSERT INTO public.base2_review_maintenance_capability
 SELECT pg_backend_pid(),txid_current(),'sitecontent_reviewapproval',r.id,'DELETE',to_jsonb(r),NULL
 FROM public.sitecontent_reviewapproval r WHERE record_id=p_record AND site_id=p_site;
 DELETE FROM public.sitecontent_reviewapproval WHERE record_id=p_record AND site_id=p_site;
 GET DIAGNOSTICS approvals=ROW_COUNT;
 DELETE FROM public.sitecontent_reviewsubject WHERE record_id=p_record AND site_id=p_site;
 GET DIAGNOSTICS subjects=ROW_COUNT;
 DELETE FROM public.base2_review_maintenance_capability WHERE backend=pg_backend_pid() AND transaction_id=txid_current();
 INSERT INTO public.sitecontent_workspaceauditevent
 (id,site_id,actor_ref,object_type,object_ref,action,outcome,correlation_id,metadata,created_at)
 VALUES(gen_random_uuid(),p_site,'system:retention','content_record',p_record::text,
 'content.review_history_retained_purge','accepted','',
 jsonb_build_object('approvals',approvals,'subjects',subjects,'intents',intents,'deliveries',deliveries),NOW());
 RETURN jsonb_build_object('approvals',approvals,'subjects',subjects,'intents',intents,'deliveries',deliveries);
END $$;
ALTER FUNCTION public.base2_apply_data_rights_subject_action(uuid,uuid,text,jsonb)
 RENAME TO base2_apply_data_rights_subject_action_legacy_0031;
CREATE FUNCTION public.base2_apply_data_rights_subject_action(
 requested_id uuid,requested_claim_token uuid,requested_action text,requested_fields jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE rights record; anonymous uuid; changed integer; counts jsonb:='{}'; result jsonb; item record;
BEGIN
 IF session_user<>'__DATA__' THEN RAISE EXCEPTION 'data_rights_role_required'; END IF;
 PERFORM pg_advisory_xact_lock(hashtext('base2-workspace-policy-v1'));
 SELECT * INTO rights FROM public.api_data_rights_operations
 WHERE id=requested_id AND claim_token=requested_claim_token AND status='running'
 AND claim_expires_at>=NOW() AND retention_until>NOW() FOR UPDATE;
 IF NOT FOUND OR rights.kind<>requested_action THEN RAISE EXCEPTION 'data_rights_claim_invalid'; END IF;
 -- Existing apply caller is unbound: only the verified durable claim supplies scope.
 PERFORM set_config('app.tenant_id',rights.tenant_id,true);
 IF requested_action IN ('deletion','global_deletion') THEN
  anonymous:=gen_random_uuid();
  WHILE EXISTS(SELECT 1 FROM public.api_auth_users WHERE id=anonymous) LOOP anonymous:=gen_random_uuid(); END LOOP;
  -- Reset every affected authorization before pseudonymizing its supporting history.
  FOR item IN SELECT r.* FROM public.sitecontent_reviewsubject r
   WHERE (r.site_id=rights.tenant_id OR requested_action='global_deletion') AND
   (rights.user_id=ANY(ARRAY[r.original_creator_id,r.semantic_author_id,r.submitter_id,r.scheduled_by_id])
    OR EXISTS(SELECT 1 FROM public.sitecontent_reviewapproval a WHERE a.record_id=r.record_id
       AND a.site_id=r.site_id AND a.reviewer_id=rights.user_id)) FOR UPDATE
  LOOP
   INSERT INTO public.base2_review_maintenance_capability
   SELECT pg_backend_pid(),txid_current(),'sitecontent_reviewsubject',r.id,'UPDATE',to_jsonb(r),
    to_jsonb(r)||jsonb_build_object(
      'original_creator_id',CASE WHEN r.original_creator_id=rights.user_id THEN NULL ELSE r.original_creator_id END,
      'semantic_author_id',CASE WHEN r.semantic_author_id=rights.user_id THEN NULL ELSE r.semantic_author_id END,
      'semantic_generation',r.semantic_generation+1,'semantic_revision',gen_random_uuid(),
      'submitter_id',NULL,'submission_id',NULL,'submitted_at',NULL,'scheduled_by_id',NULL,
      'schedule_policy_version',NULL,'fingerprint',repeat('0',64),'updated_at',NOW())
   FROM public.sitecontent_reviewsubject r WHERE r.id=item.id;
   UPDATE public.sitecontent_reviewsubject r SET
    original_creator_id=(c.new_row->>'original_creator_id')::uuid,
    semantic_author_id=(c.new_row->>'semantic_author_id')::uuid,
    semantic_generation=r.semantic_generation+1,semantic_revision=(c.new_row->>'semantic_revision')::uuid,
    submitter_id=NULL,submission_id=NULL,submitted_at=NULL,scheduled_by_id=NULL,
    schedule_policy_version=NULL,fingerprint=repeat('0',64),updated_at=NOW()
   FROM public.base2_review_maintenance_capability c WHERE r.id=item.id AND c.row_id=r.id
    AND c.backend=pg_backend_pid() AND c.transaction_id=txid_current() AND c.table_name='sitecontent_reviewsubject';
   counts:=jsonb_set(counts,'{subjects}',to_jsonb(COALESCE((counts->>'subjects')::integer,0)+1));
  END LOOP;
  INSERT INTO public.base2_review_maintenance_capability
  SELECT pg_backend_pid(),txid_current(),'sitecontent_reviewapproval',r.id,'UPDATE',to_jsonb(r),
   to_jsonb(r)||jsonb_build_object('reviewer_id',anonymous)
  FROM public.sitecontent_reviewapproval r WHERE reviewer_id=rights.user_id
   AND (site_id=rights.tenant_id OR requested_action='global_deletion');
  UPDATE public.sitecontent_reviewapproval SET reviewer_id=anonymous WHERE reviewer_id=rights.user_id
   AND (site_id=rights.tenant_id OR requested_action='global_deletion');
  GET DIAGNOSTICS changed=ROW_COUNT; counts:=counts||jsonb_build_object('approvals',changed);
  UPDATE public.sitecontent_reviewdigestbatch SET recipient_id=anonymous WHERE recipient_id=rights.user_id
   AND (site_id=rights.tenant_id OR requested_action='global_deletion');
  GET DIAGNOSTICS changed=ROW_COUNT; counts:=counts||jsonb_build_object('batches',changed);
  UPDATE public.sitecontent_reviewnotificationintent SET recipient_id=anonymous,
   status=CASE WHEN status IN ('pending','digest') THEN 'suppressed' ELSE status END,
   last_error_code='',updated_at=NOW() WHERE recipient_id=rights.user_id
   AND (site_id=rights.tenant_id OR requested_action='global_deletion');
  GET DIAGNOSTICS changed=ROW_COUNT; counts:=counts||jsonb_build_object('intents',changed);
  UPDATE public.sitecontent_reviewnotificationdelivery SET recipient_id=anonymous WHERE recipient_id=rights.user_id
   AND (site_id=rights.tenant_id OR requested_action='global_deletion');
  GET DIAGNOSTICS changed=ROW_COUNT; counts:=counts||jsonb_build_object('deliveries',changed);
  DELETE FROM public.base2_review_maintenance_capability WHERE backend=pg_backend_pid() AND transaction_id=txid_current();
  INSERT INTO public.sitecontent_workspaceauditevent
   (id,site_id,actor_ref,object_type,object_ref,action,outcome,correlation_id,metadata,created_at)
   VALUES(gen_random_uuid(),rights.tenant_id,'system:data-rights','data_rights_operation',rights.id::text,
    'content.review_maintenance','accepted','',counts,NOW());
 END IF;
 result:=public.base2_apply_data_rights_subject_action_legacy_0031(requested_id,requested_claim_token,requested_action,requested_fields);
 RETURN result||jsonb_build_object('review_history',counts);
END $$;
ALTER FUNCTION public.base2_export_data_rights_subject_surfaces()
 RENAME TO base2_export_data_rights_subject_surfaces_legacy_0031;
CREATE FUNCTION public.base2_export_data_rights_subject_surfaces()
RETURNS TABLE(table_name text,column_name text,treatment text,row_data jsonb)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE rights record;
BEGIN
 IF session_user<>'__DATA__' THEN RAISE EXCEPTION 'data_rights_role_required'; END IF;
 SELECT * INTO rights FROM public.api_data_rights_operations
 WHERE id=NULLIF(current_setting('app.data_rights_operation_id',true),'')::uuid
 AND claim_token=NULLIF(current_setting('app.data_rights_claim_token',true),'')::uuid
 AND status='running' AND claim_expires_at>=NOW() AND retention_until>NOW()
 AND tenant_id=current_setting('app.tenant_id',true)
 AND kind IN ('export','correction','deletion');
 IF NOT FOUND THEN RAISE EXCEPTION 'data_rights_claim_invalid'; END IF;
 RETURN QUERY SELECT * FROM public.base2_export_data_rights_subject_surfaces_legacy_0031();
 __EXPORT_TYPED__
END $$;
"""
SQL = SQL.replace('__EXPORT_TYPED__', '\n'.join(
    f"RETURN QUERY SELECT '{table}'::text,'{column}'::text,'pseudonymize'::text,to_jsonb(r) "
    f"FROM public.{table} r WHERE r.site_id=rights.tenant_id AND r.{column}=rights.user_id ORDER BY r.id LIMIT 1001;"
    for table, columns in SUBJECT_COLUMNS.items() for column in columns
))

SIGNATURES = (
 'base2_review_maintenance_allowed(text,uuid,text,jsonb,jsonb)',
 'base2_purge_review_history(text,uuid)',
 'base2_apply_data_rights_subject_action(uuid,uuid,text,jsonb)',
 'base2_apply_data_rights_subject_action_legacy_0031(uuid,uuid,text,jsonb)',
 'base2_export_data_rights_subject_surfaces()',
 'base2_export_data_rights_subject_surfaces_legacy_0031()',
)


def configure(apps, editor):
    if editor.connection.vendor != 'postgresql':
        return
    helper = importlib.import_module('sitecontent.migrations.0031_data_rights_worker_scope')
    worker, quoted_worker = helper._role(editor, 'WORKSPACE_WORKER_DB_USER')
    data, quoted_data = helper._role(editor, 'DATA_RIGHTS_WORKER_DB_USER')
    private_roles = [quoted_worker, quoted_data]
    for variable in ('WORKSPACE_DB_USER', 'API_RUNTIME_DB_USER', 'RUNTIME_WORKER_DB_USER'):
        private_roles.append(helper._role(editor, variable)[1])
    with editor.connection.cursor() as cursor:
        cursor.execute('SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user')
        if not cursor.fetchone()[0]:
            raise RuntimeError('review_maintenance:migration_owner_rls_capability_required')
        cursor.execute(SQL.replace('__WORKER__', worker).replace('__DATA__', data))
        cursor.execute('REVOKE ALL ON public.base2_review_maintenance_capability FROM ' + ','.join(private_roles))
        # Renames retain old ACLs: revoke legacy wrappers too, from their former caller.
        for signature in SIGNATURES:
            cursor.execute(f'REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC,' + ','.join(private_roles))
        cursor.execute(f'GRANT EXECUTE ON FUNCTION public.base2_purge_review_history(text,uuid) TO {quoted_worker}')
        cursor.execute(f'GRANT EXECUTE ON FUNCTION public.base2_apply_data_rights_subject_action(uuid,uuid,text,jsonb) TO {quoted_data}')
        cursor.execute(f'GRANT EXECUTE ON FUNCTION public.base2_export_data_rights_subject_surfaces() TO {quoted_data}')


def reverse(apps, editor):
    if editor.connection.vendor == 'postgresql':
        raise RuntimeError('review_maintenance:rollback_requires_enforcing_source_and_operator_plan')


class Migration(migrations.Migration):
    dependencies = [('sitecontent', '0038_workspace_policy_guards')]
    operations = [migrations.RunPython(configure, reverse)]
