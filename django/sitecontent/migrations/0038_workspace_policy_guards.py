"""Database enforcement for native/bulk writes and public legacy adapters.

One feature-wide advisory transaction lock deliberately trades throughput for a
consistent native/API lock order. No provider or artifact IO may hold this lock.
"""

import importlib

from django.db import migrations

SQL = r"""
CREATE OR REPLACE FUNCTION public.base2_review_maintenance_allowed(
 p_table text,p_id uuid,p_action text,p_old jsonb,p_new jsonb)
RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,public AS $$ SELECT
false $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_member(p_site text,p_user uuid,p_permission
text,p_lock boolean DEFAULT false)
RETURNS TABLE(organization_id uuid,role text) LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
BEGIN
  IF p_site IS DISTINCT FROM current_setting('app.tenant_id',true) THEN RETURN; END IF;
  IF p_permission IS NULL OR p_permission NOT IN
('read','write','publish','schedule','review','policy_read','policy_write') THEN RETURN; END IF;
  IF p_lock THEN
    PERFORM 1 FROM public.api_identity_organizations o
      JOIN public.api_identity_memberships m ON m.organization_id=o.id
      JOIN public.api_auth_users u ON u.id=m.user_id
      WHERE o.tenant_id=p_site AND u.id=p_user FOR SHARE OF o,m,u;
  END IF;
  RETURN QUERY SELECT o.id,m.role FROM public.api_identity_organizations o
    JOIN public.api_identity_memberships m ON m.organization_id=o.id
    JOIN public.api_auth_users u ON u.id=m.user_id
    WHERE o.tenant_id=p_site AND u.id=p_user AND u.is_active AND m.status='active'
      AND CASE WHEN p_permission IN ('publish','review','policy_write') THEN m.role IN
('owner','admin')
               WHEN p_permission IN ('write','schedule') THEN m.role IN ('owner','admin','editor')
               ELSE m.role IN ('owner','admin','editor','viewer') END;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_reviewers(p_site text,p_exclusions uuid[])
RETURNS SETOF uuid LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
  SELECT u.id FROM public.api_identity_organizations o
  JOIN public.api_identity_memberships m ON m.organization_id=o.id
  JOIN public.api_auth_users u ON u.id=m.user_id
  WHERE p_site=current_setting('app.tenant_id',true) AND o.tenant_id=p_site
    AND u.is_active AND m.status='active' AND m.role IN ('owner','admin')
    AND NOT(u.id=ANY(COALESCE(p_exclusions,'{}'::uuid[]))) ORDER BY u.id
$$;
CREATE OR REPLACE FUNCTION public.base2_workspace_product_delivery(p_site text,p_user uuid)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE choice text;
BEGIN
  IF NOT EXISTS(SELECT 1 FROM public.base2_workspace_member(p_site,p_user,'review',true)) THEN
RETURN 'disabled'; END IF;
  PERFORM 1 FROM public.api_notification_preference_sets WHERE tenant_id=p_site AND
user_id=p_user FOR SHARE;
  SELECT delivery INTO choice FROM public.api_notification_preferences
    WHERE tenant_id=p_site AND user_id=p_user AND event_family='product' AND channel='email';
  RETURN COALESCE(choice,'disabled');
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_effect_lock()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext('base2-workspace-policy-v1'));
  RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_actor()
RETURNS uuid LANGUAGE plpgsql STABLE SET search_path=pg_catalog,public AS $$
BEGIN
  RETURN NULLIF(current_setting('app.workspace_actor',true),'')::uuid;
EXCEPTION WHEN invalid_text_representation THEN RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_approval_valid(p_site text,p_record
uuid,p_actor uuid,p_permission text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE valid boolean;
BEGIN
  IF NOT EXISTS(SELECT 1 FROM public.base2_workspace_member(p_site,p_actor,p_permission,true))
THEN RETURN false; END IF;
  SELECT EXISTS(SELECT 1 FROM public.sitecontent_reviewsubject s
      JOIN public.sitecontent_workspacepolicy p ON p.site_id=s.site_id
      JOIN public.sitecontent_reviewapproval a ON a.record_id=s.record_id AND a.site_id=s.site_id
      WHERE s.site_id=p_site AND s.record_id=p_record AND p.schema_version=1
        AND p.organization_id=(SELECT organization_id FROM
public.base2_workspace_member(p_site,p_actor,p_permission,false))
        AND s.semantic_author_id IS NOT NULL AND s.submitter_id IS NOT NULL
        AND (s.original_creator_id IS NOT NULL OR s.adopted_snapshot)
        AND a.subject_revision=s.semantic_revision AND a.semantic_generation=s.semantic_generation
        AND a.fingerprint=s.fingerprint AND a.policy_version=p.version
        AND a.reviewer_id IS DISTINCT FROM s.original_creator_id
        AND a.reviewer_id IS DISTINCT FROM s.semantic_author_id AND a.reviewer_id IS DISTINCT
FROM s.submitter_id
        AND EXISTS(SELECT 1 FROM
public.base2_workspace_member(p_site,a.reviewer_id,'review',true))) INTO valid;
  RETURN valid;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_policy_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE org uuid;
BEGIN
  SELECT organization_id INTO org FROM public.base2_workspace_member(
    NEW.site_id,public.base2_workspace_actor(),'policy_write',true);
  IF org IS NULL OR NEW.organization_id IS DISTINCT FROM org THEN
    RAISE EXCEPTION 'workspace_policy_authorization_required' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' AND (NEW.site_id IS DISTINCT FROM OLD.site_id OR NEW.version<>OLD.version+1)
THEN
    RAISE EXCEPTION 'workspace_policy_version_invalid' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_policy_audit(
 p_site text,p_actor uuid,p_expected bigint,p_version bigint)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE org uuid;
BEGIN
 SELECT organization_id INTO org FROM
 public.base2_workspace_member(p_site,p_actor,'policy_write',true);
 IF org IS NULL OR p_actor IS DISTINCT FROM public.base2_workspace_actor()
   OR p_version<>p_expected+1 OR NOT EXISTS(SELECT 1 FROM public.sitecontent_workspacepolicy
     WHERE site_id=p_site AND organization_id=org AND version=p_version) THEN
   RAISE EXCEPTION 'workspace_policy_audit_scope_invalid' USING ERRCODE='23514';
 END IF;
 INSERT INTO public.api_auth_audit_events(id,user_id,action,ip,user_agent,metadata_json)
 VALUES(gen_random_uuid(),p_actor,'workspace.policy_updated','','',jsonb_build_object(
   'tenant_id',p_site,'organization_id',org,'expected_version',p_expected,'version',p_version));
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_review_audit(
 p_site text,p_actor uuid,p_action text,p_record uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE org uuid; record_version bigint;
BEGIN
 IF p_action NOT IN ('content.review_approved','content.review_subject_adopted',
 'content.review_requested') THEN RAISE EXCEPTION 'workspace_review_audit_invalid'; END IF;
 SELECT organization_id INTO org FROM public.base2_workspace_member(p_site,p_actor,
 CASE WHEN p_action='content.review_approved' THEN 'review' ELSE 'write' END,true);
 SELECT version INTO record_version FROM public.sitecontent_contentrecord
 WHERE site_id=p_site AND id=p_record;
 IF org IS NULL OR record_version IS NULL
 OR p_actor IS DISTINCT FROM public.base2_workspace_actor() THEN
 RAISE EXCEPTION 'workspace_review_audit_scope_invalid'; END IF;
 INSERT INTO public.api_auth_audit_events(id,user_id,action,ip,user_agent,metadata_json)
 VALUES(gen_random_uuid(),p_actor,p_action,'','',jsonb_build_object(
 'tenant_id',p_site,'organization_id',org,'record_id',p_record,'record_version',record_version));
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_definition_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE protected boolean; previous jsonb:=to_jsonb(OLD); incoming jsonb:=to_jsonb(NEW);
BEGIN
  protected:=OLD.status IN ('published','retired') OR EXISTS(
    SELECT 1 FROM public.sitecontent_contentrecord WHERE definition_id=OLD.id);
  IF protected THEN
    IF TG_OP='DELETE' THEN
      RAISE EXCEPTION 'published_definition_immutable' USING ERRCODE='23514';
    END IF;
    IF (incoming-ARRAY['status','lock_version','updated_by','updated_at']) IS DISTINCT FROM
       (previous-ARRAY['status','lock_version','updated_by','updated_at'])
       OR NOT (NEW.status=OLD.status OR (OLD.status='published' AND NEW.status='retired')) THEN
      RAISE EXCEPTION 'published_definition_immutable' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN COALESCE(NEW,OLD);
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_field_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE parent record; previous_site text;
BEGIN
  FOR parent IN SELECT d.id,d.site_id,d.status FROM public.sitecontent_contenttypedefinition d
    WHERE d.id IN ((to_jsonb(NEW)->>'definition_id')::uuid,
                   (to_jsonb(OLD)->>'definition_id')::uuid) ORDER BY d.id FOR UPDATE
  LOOP
    IF parent.status IN ('published','retired') OR EXISTS(
        SELECT 1 FROM public.sitecontent_contentrecord WHERE definition_id=parent.id) THEN
      RAISE EXCEPTION 'published_definition_immutable' USING ERRCODE='23514';
    END IF;
    IF previous_site IS NOT NULL AND parent.site_id IS DISTINCT FROM previous_site THEN
      RAISE EXCEPTION 'content_definition_scope_invalid' USING ERRCODE='23514';
    END IF;
    previous_site:=parent.site_id;
  END LOOP;
  RETURN COALESCE(NEW,OLD);
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_record_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE required boolean; semantic_change boolean:=false; actor uuid; scheduled_actor uuid;
worker_fallback boolean:=false;
BEGIN
  IF TG_OP='UPDATE' AND OLD.definition_id IS NOT NULL AND
    (NEW.definition_id IS NULL OR NEW.site_id IS DISTINCT FROM OLD.site_id) THEN
    RAISE EXCEPTION 'workspace_managed_scope_immutable' USING ERRCODE='23514';
  END IF;
  IF NEW.definition_id IS NULL THEN RETURN NEW; END IF;
  IF NOT EXISTS(SELECT 1 FROM public.sitecontent_contenttypedefinition
    WHERE id=NEW.definition_id AND site_id=NEW.site_id) THEN
    RAISE EXCEPTION 'content_definition_scope_invalid' USING ERRCODE='23514';
  END IF;
  SELECT require_review INTO required FROM public.sitecontent_workspacepolicy
    WHERE site_id=NEW.site_id AND schema_version=1 FOR UPDATE;
  required:=COALESCE(required,true);
  IF TG_OP='UPDATE' THEN
    semantic_change:=ROW(NEW.content_type,NEW.definition_id,NEW.schema_version,NEW.title,NEW.slug,
      NEW.excerpt,NEW.body,NEW.metadata,NEW.values,NEW.sitemap_include,NEW.search_visible)
      IS DISTINCT FROM
ROW(OLD.content_type,OLD.definition_id,OLD.schema_version,OLD.title,OLD.slug,
      OLD.excerpt,OLD.body,OLD.metadata,OLD.values,OLD.sitemap_include,OLD.search_visible);
    IF semantic_change AND required AND NEW.state IN ('published','scheduled','in_review') THEN
      NEW.state:='draft'; NEW.publish_at:=NULL; NEW.schedule_timezone:='';
    END IF;
  END IF;
  IF TG_OP='UPDATE' AND NEW.definition_id IS NOT NULL THEN
    IF NEW.deleted_at IS DISTINCT FROM OLD.deleted_at AND NEW.state='published' THEN
      RAISE EXCEPTION 'content_restore_requires_draft' USING ERRCODE='23514';
    END IF;
    IF NEW.state='scheduled' AND OLD.state='scheduled' AND
      ROW(NEW.publish_at,NEW.schedule_timezone) IS DISTINCT FROM
ROW(OLD.publish_at,OLD.schedule_timezone) THEN
      IF NOT EXISTS(SELECT 1 FROM
public.base2_workspace_member(NEW.site_id,public.base2_workspace_actor(),'schedule',true))
        OR (required AND NOT
public.base2_workspace_approval_valid(NEW.site_id,NEW.id,public.base2_workspace_actor(),'schedule'))
THEN
        RAISE EXCEPTION 'content_schedule_authorization_required' USING ERRCODE='23514';
      END IF;
      UPDATE public.sitecontent_reviewsubject SET scheduled_by_id=public.base2_workspace_actor(),
        schedule_policy_version=(SELECT version FROM public.sitecontent_workspacepolicy WHERE
site_id=NEW.site_id)
        WHERE site_id=NEW.site_id AND record_id=NEW.id;
    END IF;
  END IF;
  IF required AND NEW.state IN ('published','scheduled') AND
      (TG_OP='INSERT' OR NEW.state IS DISTINCT FROM OLD.state) THEN
    actor:=public.base2_workspace_actor();
    IF NEW.state='published' AND TG_OP='UPDATE' AND OLD.state='scheduled' THEN
      SELECT scheduled_by_id INTO scheduled_actor FROM public.sitecontent_reviewsubject
        WHERE record_id=NEW.id AND site_id=NEW.site_id;
      IF actor IS NULL THEN
        IF session_user<>'__WORKER_ROLE__' THEN
          RAISE EXCEPTION 'content_publication_actor_required' USING ERRCODE='23514';
        END IF;
        worker_fallback:=true;
        IF OLD.publish_at IS NULL OR OLD.publish_at>NOW() THEN
          RAISE EXCEPTION 'content_schedule_not_due' USING ERRCODE='23514';
        END IF;
        actor:=scheduled_actor;
      END IF;
      IF NOT
public.base2_workspace_approval_valid(NEW.site_id,NEW.id,scheduled_actor,'schedule') THEN
        RAISE EXCEPTION 'content_review_required' USING ERRCODE='23514';
      END IF;
    END IF;
    IF NOT public.base2_workspace_approval_valid(NEW.site_id,NEW.id,actor,
        CASE WHEN NEW.state='scheduled' OR worker_fallback THEN 'schedule' ELSE 'publish' END)
THEN
      RAISE EXCEPTION 'content_review_required' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_record_subject()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE actor uuid; changed boolean;
BEGIN
  IF NEW.definition_id IS NULL THEN RETURN NEW; END IF;
  actor:=public.base2_workspace_actor();
  IF NOT EXISTS(SELECT 1 FROM public.base2_workspace_member(NEW.site_id,actor,'write',true))
THEN actor:=NULL; END IF;
  IF TG_OP='INSERT' THEN
    INSERT INTO public.sitecontent_reviewsubject(id,site_id,record_id,schema_version,
original_creator_id,semantic_author_id,adopted_snapshot,semantic_revision,semantic_generation,
      fingerprint,created_at,updated_at) VALUES
(gen_random_uuid(),NEW.site_id,NEW.id,1,actor,actor,false,gen_random_uuid(),1,repeat('0',64),NOW(),NOW());
  ELSE
    changed:=ROW(NEW.content_type,NEW.definition_id,NEW.schema_version,NEW.title,NEW.slug,
      NEW.excerpt,NEW.body,NEW.metadata,NEW.values,NEW.sitemap_include,NEW.search_visible)
      IS DISTINCT FROM
ROW(OLD.content_type,OLD.definition_id,OLD.schema_version,OLD.title,OLD.slug,
      OLD.excerpt,OLD.body,OLD.metadata,OLD.values,OLD.sitemap_include,OLD.search_visible);
    IF changed OR (NEW.state IS DISTINCT FROM OLD.state
      AND NEW.state IN ('draft','archived','deleted')) THEN
      UPDATE public.sitecontent_reviewsubject SET semantic_revision=gen_random_uuid(),
        semantic_generation=semantic_generation+CASE WHEN changed THEN 1 ELSE 0 END,
        semantic_author_id=CASE WHEN changed THEN actor ELSE semantic_author_id END,
        submitter_id=NULL,
        submission_id=NULL,submitted_at=NULL,
        fingerprint=CASE WHEN changed THEN repeat('0',64) ELSE fingerprint END,scheduled_by_id=NULL,
        schedule_policy_version=NULL,updated_at=NOW() WHERE record_id=NEW.id AND
site_id=NEW.site_id;
      IF NOT FOUND THEN
        INSERT INTO public.sitecontent_reviewsubject(id,site_id,record_id,schema_version,
semantic_author_id,adopted_snapshot,semantic_revision,semantic_generation,fingerprint,created_at,updated_at)
VALUES(gen_random_uuid(),NEW.site_id,NEW.id,1,actor,false,gen_random_uuid(),1,repeat('0',64),NOW(),NOW());
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_binding_changed()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE target uuid; scope text; actor uuid;
BEGIN
  actor:=public.base2_workspace_actor();
  FOR target,scope IN SELECT DISTINCT x.id,x.site FROM (VALUES
    (CASE WHEN TG_OP<>'INSERT' THEN (to_jsonb(OLD)->>TG_ARGV[0])::uuid END,CASE WHEN
TG_OP<>'INSERT' THEN OLD.site_id END),
    (CASE WHEN TG_OP<>'DELETE' THEN (to_jsonb(NEW)->>TG_ARGV[0])::uuid END,CASE WHEN
TG_OP<>'DELETE' THEN NEW.site_id END)) x(id,site)
    WHERE x.id IS NOT NULL ORDER BY x.id
  LOOP
    PERFORM 1 FROM public.sitecontent_workspacepolicy WHERE site_id=scope FOR UPDATE;
    PERFORM 1 FROM public.sitecontent_contentrecord WHERE id=target AND site_id=scope FOR UPDATE;
    UPDATE public.sitecontent_reviewsubject SET semantic_generation=semantic_generation+1,
      semantic_revision=gen_random_uuid(),fingerprint=repeat('0',64),semantic_author_id=CASE
        WHEN EXISTS(SELECT 1 FROM public.base2_workspace_member(scope,actor,'write',true)) THEN
actor ELSE NULL END,
submitter_id=NULL,submission_id=NULL,submitted_at=NULL,scheduled_by_id=NULL,schedule_policy_version=NULL,
      updated_at=NOW() WHERE record_id=target AND site_id=scope;
    UPDATE public.sitecontent_contentrecord SET state='draft',publish_at=NULL,schedule_timezone=''
      WHERE id=target AND site_id=scope AND state IN ('published','scheduled','in_review')
      AND COALESCE((SELECT require_review FROM public.sitecontent_workspacepolicy WHERE
site_id=scope),true);
  END LOOP;
  RETURN COALESCE(NEW,OLD);
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_approval_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE subject public.sitecontent_reviewsubject; policy public.sitecontent_workspacepolicy;
BEGIN
  IF TG_OP<>'INSERT' THEN
    IF
public.base2_review_maintenance_allowed(TG_TABLE_NAME,OLD.id,TG_OP,to_jsonb(OLD),to_jsonb(NEW))
THEN
      RETURN COALESCE(NEW,OLD);
    END IF;
    RAISE EXCEPTION 'content_approval_immutable' USING ERRCODE='23514';
  END IF;
  SELECT * INTO policy FROM public.sitecontent_workspacepolicy WHERE site_id=NEW.site_id FOR
UPDATE;
  SELECT * INTO subject FROM public.sitecontent_reviewsubject WHERE record_id=NEW.record_id AND
site_id=NEW.site_id;
  IF NOT FOUND OR NEW.reviewer_id IS DISTINCT FROM public.base2_workspace_actor()
    OR NOT EXISTS(SELECT 1 FROM
public.base2_workspace_member(NEW.site_id,NEW.reviewer_id,'review',true))
    OR NOT EXISTS(SELECT 1 FROM public.sitecontent_contentrecord WHERE id=NEW.record_id AND
site_id=NEW.site_id AND state='in_review')
    OR subject.semantic_author_id IS NULL OR subject.submitter_id IS NULL
    OR (subject.original_creator_id IS NULL AND NOT subject.adopted_snapshot)
    OR
NEW.reviewer_id=ANY(ARRAY[subject.original_creator_id,subject.semantic_author_id,subject.submitter_id])
    OR NEW.subject_revision IS DISTINCT FROM subject.semantic_revision
    OR NEW.semantic_generation IS DISTINCT FROM subject.semantic_generation
    OR NEW.fingerprint IS DISTINCT FROM subject.fingerprint OR NEW.fingerprint=repeat('0',64)
    OR NEW.policy_version IS DISTINCT FROM policy.version THEN
    RAISE EXCEPTION 'content_review_invalid' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_media_scope()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE data jsonb:=to_jsonb(NEW); previous jsonb:=to_jsonb(OLD);
BEGIN
  IF TG_OP='UPDATE' AND (data->>'id' IS DISTINCT FROM previous->>'id'
    OR data->>'asset_id' IS DISTINCT FROM previous->>'asset_id'
    OR data->>'site_id' IS DISTINCT FROM previous->>'site_id') THEN
    RAISE EXCEPTION 'content_asset_scope_immutable' USING ERRCODE='23514';
  END IF;
  IF TG_TABLE_NAME='sitecontent_mediaobjectversion' AND NOT EXISTS(
    SELECT 1 FROM public.sitecontent_mediaasset
    WHERE id=(data->>'asset_id')::uuid AND site_id=data->>'site_id') THEN
    RAISE EXCEPTION 'content_asset_scope_invalid' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_media_changed()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE bound record; asset uuid;
BEGIN
  asset:=COALESCE(to_jsonb(NEW),to_jsonb(OLD))->>CASE WHEN
TG_TABLE_NAME='sitecontent_mediaasset' THEN 'id' ELSE 'asset_id' END;
  FOR bound IN SELECT b.record_id,b.site_id FROM public.sitecontent_assetbinding b
    WHERE b.asset_id=asset ORDER BY b.record_id
  LOOP
    PERFORM 1 FROM public.sitecontent_workspacepolicy WHERE site_id=bound.site_id FOR UPDATE;
    PERFORM 1 FROM public.sitecontent_contentrecord WHERE id=bound.record_id FOR UPDATE;
    UPDATE public.sitecontent_reviewsubject SET semantic_generation=semantic_generation+1,
      semantic_revision=gen_random_uuid(),fingerprint=repeat('0',64),semantic_author_id=CASE
        WHEN EXISTS(SELECT 1 FROM
public.base2_workspace_member(bound.site_id,public.base2_workspace_actor(),'write',true))
        THEN public.base2_workspace_actor() ELSE NULL END,submitter_id=NULL,submission_id=NULL,
      submitted_at=NULL,scheduled_by_id=NULL,schedule_policy_version=NULL,updated_at=NOW()
      WHERE record_id=bound.record_id AND site_id=bound.site_id;
    UPDATE public.sitecontent_contentrecord SET state='draft',publish_at=NULL,schedule_timezone=''
      WHERE id=bound.record_id AND state IN ('published','scheduled','in_review')
      AND COALESCE((SELECT require_review FROM public.sitecontent_workspacepolicy WHERE
site_id=bound.site_id),true);
  END LOOP;
  RETURN COALESCE(NEW,OLD);
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_review_scope()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE data jsonb:=to_jsonb(NEW);
BEGIN
  IF TG_TABLE_NAME='sitecontent_reviewsubject' AND TG_OP='UPDATE' AND NOT
public.base2_review_maintenance_allowed(TG_TABLE_NAME,OLD.id,TG_OP,to_jsonb(OLD),to_jsonb(NEW))
THEN
    IF data->>'submission_id' IS NOT NULL
      AND data->>'submission_id' IS DISTINCT FROM to_jsonb(OLD)->>'submission_id'
      AND data->>'semantic_revision' IS NOT DISTINCT FROM to_jsonb(OLD)->>'semantic_revision' THEN
      RAISE EXCEPTION 'content_review_cycle_invalid' USING ERRCODE='23514';
    END IF;
    IF data->>'original_creator_id' IS DISTINCT FROM to_jsonb(OLD)->>'original_creator_id'
      OR (data->>'semantic_generation')::bigint <
(to_jsonb(OLD)->>'semantic_generation')::bigint THEN
      RAISE EXCEPTION 'content_review_provenance_immutable' USING ERRCODE='23514';
    END IF;
  END IF;
  IF data->>'record_id' IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.sitecontent_contentrecord
    WHERE id=(data->>'record_id')::uuid AND site_id=NEW.site_id AND definition_id IS NOT NULL)
THEN
    RAISE EXCEPTION 'content_review_scope_invalid' USING ERRCODE='23514'; END IF;
  IF data->>'digest_batch_id' IS NOT NULL AND NOT EXISTS(SELECT 1 FROM
public.sitecontent_reviewdigestbatch
    WHERE id=(data->>'digest_batch_id')::uuid AND site_id=NEW.site_id AND
recipient_id=(data->>'recipient_id')::uuid) THEN
    RAISE EXCEPTION 'content_review_scope_invalid' USING ERRCODE='23514'; END IF;
  IF TG_TABLE_NAME='sitecontent_reviewnotificationdelivery' AND data->>'intent_id' IS NOT NULL
AND NOT EXISTS(
    SELECT 1 FROM public.sitecontent_reviewnotificationintent WHERE id=(data->>'intent_id')::uuid
      AND site_id=NEW.site_id AND recipient_id=(data->>'recipient_id')::uuid) THEN
    RAISE EXCEPTION 'content_review_scope_invalid' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_relation_scope()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
DECLARE data jsonb:=to_jsonb(NEW); parent uuid; target uuid;
BEGIN
  parent:=COALESCE(data->>'record_id',data->>'source_id')::uuid;
  IF NOT EXISTS(SELECT 1 FROM public.sitecontent_contentrecord WHERE id=parent AND
site_id=NEW.site_id) THEN
    RAISE EXCEPTION 'content_relationship_scope_invalid' USING ERRCODE='23514'; END IF;
  IF TG_TABLE_NAME='sitecontent_assetbinding' THEN
    IF NOT EXISTS(SELECT 1 FROM public.sitecontent_mediaasset WHERE id=(data->>'asset_id')::uuid
AND site_id=NEW.site_id) THEN
      RAISE EXCEPTION 'content_asset_scope_invalid' USING ERRCODE='23514'; END IF;
  ELSE
    IF NOT EXISTS(SELECT 1 FROM public.sitecontent_contentrecord WHERE
id=(data->>'target_id')::uuid AND site_id=NEW.site_id) THEN
      RAISE EXCEPTION 'content_relationship_scope_invalid' USING ERRCODE='23514'; END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.base2_workspace_public_asset(p_site text,p_asset uuid)
RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,public SET
row_security=off AS $$
  SELECT p_site=current_setting('app.tenant_id',true) AND NOT EXISTS(
    SELECT 1 FROM public.sitecontent_assetbinding b
    JOIN public.sitecontent_contentrecord r ON r.id=b.record_id AND r.site_id=b.site_id
    WHERE b.asset_id=p_asset AND b.site_id=p_site AND r.definition_id IS NOT NULL
      AND NOT EXISTS(SELECT 1 FROM public.sitecontent_workspacepolicy p
        WHERE p.site_id=p_site AND p.schema_version=1 AND p.public_access='public_allowed'))
$$;
"""

PROTECTED = (
    "sitecontent_contenttypedefinition",
    "sitecontent_contentfielddefinition",
    "sitecontent_workspacepolicy",
    "sitecontent_contentrecord",
    "sitecontent_assetbinding",
    "sitecontent_contentrelationship",
    "sitecontent_mediaasset",
    "sitecontent_mediavariant",
    "sitecontent_mediaobjectversion",
    "sitecontent_reviewsubject",
    "sitecontent_reviewapproval",
    "api_identity_organizations",
    "api_identity_memberships",
    "api_auth_users",
    "api_notification_preference_sets",
    "api_notification_preferences",
)
FUNCTIONS = (
    "base2_workspace_member(text,uuid,text,boolean)",
    "base2_workspace_reviewers(text,uuid[])",
    "base2_workspace_product_delivery(text,uuid)",
    "base2_workspace_effect_lock()",
    "base2_workspace_actor()",
    "base2_workspace_approval_valid(text,uuid,uuid,text)",
    "base2_workspace_record_guard()",
    "base2_workspace_definition_guard()",
    "base2_workspace_field_guard()",
    "base2_workspace_record_subject()",
    "base2_workspace_binding_changed()",
    "base2_workspace_approval_guard()",
    "base2_workspace_media_changed()",
    "base2_workspace_media_scope()",
    "base2_workspace_review_scope()",
    "base2_workspace_public_asset(text,uuid)",
    "base2_workspace_relation_scope()",
    "base2_review_maintenance_allowed(text,uuid,text,jsonb,jsonb)",
    "base2_workspace_policy_guard()",
    "base2_workspace_policy_audit(text,uuid,bigint,bigint)",
    "base2_workspace_review_audit(text,uuid,text,uuid)",
)


def configure(apps, editor):
    if editor.connection.vendor != "postgresql":
        return
    helper = importlib.import_module("sitecontent.migrations.0037_workspace_policy_runtime_roles")
    roles = helper.roles(editor)
    with editor.connection.cursor() as cur:
        # FORCE RLS must not silently hide identity rows inside authoritative helpers.
        # The existing migration-owner boundary, never a runtime role, owns helpers.
        cur.execute("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")
        if not cur.fetchone()[0]:
            raise RuntimeError("workspace_policy:migration_owner_rls_capability_required")
        cur.execute(SQL.replace("__WORKER_ROLE__", roles["worker"].strip(chr(34))))
        for signature in FUNCTIONS:
            cur.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
        for signature in FUNCTIONS[:2]:
            cur.execute(
                f"GRANT EXECUTE ON FUNCTION public.{signature} TO "
                f"{roles['request']},{roles['worker']}"
            )
        cur.execute(
            f"GRANT EXECUTE ON FUNCTION "
            f"public.base2_workspace_product_delivery(text,uuid) TO {roles['worker']}"
        )
        cur.execute(
            f"GRANT EXECUTE ON FUNCTION "
            "public.base2_workspace_approval_valid(text,uuid,uuid,text) "
            f"TO {roles['request']},{roles['worker']}"
        )
        cur.execute(
            f"GRANT EXECUTE ON FUNCTION "
            f"public.base2_workspace_public_asset(text,uuid) TO {roles['api']}"
        )
        cur.execute(
            "GRANT EXECUTE ON FUNCTION "
            "public.base2_workspace_policy_audit(text,uuid,bigint,bigint) "
            f"TO {roles['request']}"
        )
        cur.execute(
            "GRANT EXECUTE ON FUNCTION public.base2_workspace_review_audit(text,uuid,text,uuid) "
            f"TO {roles['request']}"
        )
        eligibility_updates = {
            "api_auth_users": "id,is_active",
            "api_identity_memberships": "organization_id,user_id,role,status",
            "api_identity_organizations": "id,tenant_id",
        }
        for table in PROTECTED:
            update = "UPDATE"
            if table in eligibility_updates:
                update += " OF " + eligibility_updates[table]
            cur.execute(
                f"CREATE TRIGGER workspace_effect_lock BEFORE INSERT OR {update} OR "
                f"DELETE ON {table} "
                "FOR EACH STATEMENT EXECUTE FUNCTION public.base2_workspace_effect_lock()"
            )
        cur.execute(
            "CREATE TRIGGER workspace_definition_guard BEFORE UPDATE OR DELETE ON "
            "sitecontent_contenttypedefinition FOR EACH ROW "
            "EXECUTE FUNCTION public.base2_workspace_definition_guard()"
        )
        cur.execute(
            "CREATE TRIGGER workspace_field_guard BEFORE INSERT OR UPDATE OR DELETE ON "
            "sitecontent_contentfielddefinition FOR EACH ROW "
            "EXECUTE FUNCTION public.base2_workspace_field_guard()"
        )
        cur.execute(
            "CREATE TRIGGER workspace_policy_guard BEFORE INSERT OR UPDATE ON "
            "sitecontent_workspacepolicy "
            "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_policy_guard()"
        )
        cur.execute(
            "CREATE TRIGGER workspace_record_guard BEFORE INSERT OR UPDATE ON "
            "sitecontent_contentrecord "
            "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_record_guard()"
        )
        cur.execute(
            "CREATE TRIGGER workspace_record_subject AFTER INSERT OR UPDATE "
            "ON sitecontent_contentrecord "
            "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_record_subject()"
        )
        for table, key in (
            ("sitecontent_assetbinding", "record_id"),
            ("sitecontent_contentrelationship", "source_id"),
        ):
            cur.execute(
                f"CREATE TRIGGER workspace_relation_scope BEFORE INSERT OR UPDATE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_relation_scope()"
            )
            cur.execute(
                f"CREATE TRIGGER workspace_binding_changed AFTER INSERT OR UPDATE "
                f"OR DELETE ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_binding_changed('{key}')"
            )
        for table in (
            "sitecontent_mediaasset",
            "sitecontent_mediavariant",
            "sitecontent_mediaobjectversion",
        ):
            cur.execute(
                f"CREATE TRIGGER workspace_media_scope BEFORE INSERT OR UPDATE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_media_scope()"
            )
            cur.execute(
                f"CREATE TRIGGER workspace_media_changed AFTER INSERT OR UPDATE OR "
                f"DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_media_changed()"
            )
        cur.execute(
            "CREATE TRIGGER workspace_approval_guard BEFORE INSERT OR UPDATE "
            "OR DELETE ON sitecontent_reviewapproval "
            "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_approval_guard()"
        )
        for table in (
            "sitecontent_reviewsubject",
            "sitecontent_reviewapproval",
            "sitecontent_reviewnotificationintent",
            "sitecontent_reviewnotificationdelivery",
        ):
            cur.execute(
                f"CREATE TRIGGER workspace_review_scope BEFORE INSERT OR UPDATE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION public.base2_workspace_review_scope()"
            )
        cur.execute(f"GRANT SELECT(definition_id) ON sitecontent_contentrecord TO {roles['api']}")
        cur.execute(
            f"CREATE POLICY workspace_public_visibility ON "
            f"sitecontent_contentrecord AS RESTRICTIVE "
            f"FOR SELECT TO {roles['api']} USING (definition_id IS NULL OR EXISTS "
            '(SELECT 1 FROM sitecontent_workspacepolicy p WHERE '
            'p.site_id=sitecontent_contentrecord.site_id '
            "AND p.schema_version=1 AND p.public_access='public_allowed'))"
        )
        cur.execute(
            f"CREATE POLICY workspace_public_asset_visibility ON "
            f"sitecontent_mediaasset AS RESTRICTIVE "
            f"FOR SELECT TO {roles['api']} USING (public.base2_workspace_public_asset(site_id,id))"
        )
        # Existing search predicate joins content records and therefore intersects this policy.


def reverse(apps, editor):
    if editor.connection.vendor == "postgresql":
        raise RuntimeError("workspace_policy:rollback_requires_enforcing_source_and_operator_plan")


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0037_workspace_policy_runtime_roles")]
    operations = [migrations.RunPython(configure, reverse)]
