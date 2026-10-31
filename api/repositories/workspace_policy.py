"""Runtime adapter for canonical shared policy and review state.

Every effect takes the feature transaction lock before policy/content/member locks.
No email or external storage operation belongs inside these transactions.
"""

from __future__ import annotations

import json
from contextlib import suppress
from uuid import UUID, uuid4

from api.db import workspace_db_conn
from api.security.content_workspace import canonical_digest
from api.settings import settings

POLICY_LOCK = 'base2-workspace-policy-v1'
SEMANTIC_FIELDS = (
    'content_type',
    'definition_id',
    'schema_version',
    'title',
    'slug',
    'excerpt',
    'body',
    'metadata',
    'values',
    'sitemap_include',
    'search_visible',
)


def semantic_fingerprint(record: dict, bindings: list, relationships: list) -> str:
    return canonical_digest(
        {
            'record': {key: record.get(key) for key in SEMANTIC_FIELDS},
            'bindings': bindings,
            'relationships': relationships,
        }
    )


def review_is_independent(subject: dict, reviewer: str) -> bool:
    authors = [
        subject.get(key) for key in ('original_creator_id', 'semantic_author_id', 'submitter_id')
    ]
    return bool(
        authors[1]
        and authors[2]
        and (authors[0] or subject.get('adopted_snapshot'))
        and str(reviewer) not in {str(value) for value in authors if value}
    )


def begin_effect(cur, *, actor_ref: str | None = None) -> None:
    cur.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (POLICY_LOCK,))
    if actor_ref is not None:
        actor = str(UUID(actor_ref.removeprefix('user:')))
        cur.execute("SELECT set_config('app.workspace_actor',%s,true)", (actor,))


def member(cur, *, site_id: str, user_id, permission: str, lock: bool = False) -> dict:
    cur.execute(
        'SELECT organization_id,role FROM base2_workspace_member(%s,%s,%s,%s)',
        (site_id, str(user_id), permission, lock),
    )
    row = cur.fetchone()
    if not row:
        raise PermissionError('workspace_policy_forbidden')
    return {'organization_id': str(row[0]), 'role': row[1]}


def read_policy(cur, *, site_id: str, lock: bool = False) -> dict:
    cur.execute(
        """SELECT schema_version,version,require_review,public_access,organization_id,provenance
                   FROM sitecontent_workspacepolicy WHERE site_id=%s"""
        + (' FOR UPDATE' if lock else ''),
        (site_id,),
    )
    row = cur.fetchone()
    if row is None:
        return {
            'schema_version': 1,
            'version': 0,
            'require_review': True,
            'public_access': 'members_only',
            'organization_id': None,
            'provenance': 'default',
        }
    if row[0] != 1:
        raise ValueError('workspace_policy_schema_unsupported')
    return {
        'schema_version': row[0],
        'version': row[1],
        'require_review': row[2],
        'public_access': row[3],
        'organization_id': str(row[4]) if row[4] else None,
        'provenance': row[5],
    }


def _envelope(policy, *, site_id, membership):
    if policy['organization_id'] and policy['organization_id'] != membership['organization_id']:
        raise ValueError('workspace_policy_scope_invalid')
    restrictions = []
    if settings.CONTENT_WORKSPACE_STORAGE_BACKEND != 'local':
        restrictions.append('storage_transport_unverified')
    return {key: value for key, value in policy.items() if key != 'organization_id'} | {
        'scope': {'site_id': site_id, 'organization_id': membership['organization_id']},
        'permissions': {'read': True, 'write': membership['role'] in {'owner', 'admin'}},
        'restrictions': restrictions,
    }


def get_policy(*, site_id: str, user_id) -> dict:
    with workspace_db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
        membership = member(cur, site_id=site_id, user_id=user_id, permission='policy_read')
        return _envelope(read_policy(cur, site_id=site_id), site_id=site_id, membership=membership)


def update_policy(
    *, site_id: str, user_id, expected_version: int, require_review: bool, public_access: str
) -> dict | None:
    if settings.CONTENT_WORKSPACE_STORAGE_BACKEND != 'local' and (
        require_review or public_access == 'members_only'
    ):
        raise ValueError('storage_transport_unverified')
    with workspace_db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                begin_effect(cur, actor_ref=f'user:{user_id}')
                policy = read_policy(cur, site_id=site_id, lock=True)
                membership = member(
                    cur, site_id=site_id, user_id=user_id, permission='policy_write', lock=True
                )
                _envelope(policy, site_id=site_id, membership=membership)
                if policy['version'] != expected_version:
                    conn.rollback()
                    return None
                if expected_version == 0:
                    cur.execute(
                        """INSERT INTO sitecontent_workspacepolicy
                        (id,site_id,organization_id,schema_version,version,require_review,public_access,
                         provenance,created_at,updated_at) VALUES (%s,%s,%s,1,1,%s,%s,'explicit',NOW(),NOW())
                         ON CONFLICT (site_id) DO NOTHING RETURNING version""",
                        (
                            str(uuid4()),
                            site_id,
                            membership['organization_id'],
                            require_review,
                            public_access,
                        ),
                    )
                else:
                    cur.execute(
                        """UPDATE sitecontent_workspacepolicy SET organization_id=%s,
                        version=version+1,require_review=%s,public_access=%s,provenance='explicit',updated_at=NOW()
                        WHERE site_id=%s AND version=%s RETURNING version""",
                        (
                            membership['organization_id'],
                            require_review,
                            public_access,
                            site_id,
                            expected_version,
                        ),
                    )
                changed = cur.fetchone()
                if not changed:
                    conn.rollback()
                    return None
                result = _envelope(
                    {
                        **policy,
                        'version': changed[0],
                        'require_review': require_review,
                        'public_access': public_access,
                        'provenance': 'explicit',
                    },
                    site_id=site_id,
                    membership=membership,
                )
                audit(
                    cur,
                    site_id=site_id,
                    actor_ref=f'user:{user_id}',
                    object_ref=site_id,
                    action='workspace.policy_updated',
                    metadata={'expected_version': expected_version, 'version': changed[0]},
                )
                cur.execute(
                    'SELECT base2_workspace_policy_audit(%s,%s,%s,%s)',
                    (site_id, str(user_id), expected_version, changed[0]),
                )
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


def audit(cur, *, site_id: str, actor_ref: str, object_ref: str, action: str, metadata=None):
    cur.execute(
        """INSERT INTO sitecontent_workspaceauditevent
        (id,site_id,actor_ref,object_type,object_ref,action,outcome,correlation_id,metadata,created_at)
        VALUES (%s,%s,%s,'workspace_policy',%s,%s,'accepted','',%s::jsonb,NOW())""",
        (str(uuid4()), site_id, actor_ref, object_ref, action, json.dumps(metadata or {})),
    )
    if action in {
        'content.review_approved',
        'content.review_subject_adopted',
        'content.review_requested',
    }:
        cur.execute(
            'SELECT base2_workspace_review_audit(%s,%s,%s,%s)',
            (site_id, actor_ref.removeprefix('user:'), action, object_ref),
        )


def current_fingerprint(cur, *, site_id: str, record_id) -> str:
    cur.execute(
        'SELECT to_jsonb(r) FROM sitecontent_contentrecord r WHERE r.site_id=%s AND r.id=%s',
        (site_id, str(record_id)),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError('content_not_found')
    record = row[0]
    cur.execute(
        """SELECT jsonb_build_object('asset_id',b.asset_id,'field_key',b.field_key,
        'order',b."order",'alt_text',b.alt_text,'caption',b.caption,'credit',b.credit,
        'focal_x',b.focal_x,'focal_y',b.focal_y,'sha256',a.sha256,'status',a.status,
        'visibility',a.visibility,'object_version',a.current_object_version,
        'object_sha256',v.sha256,'safe_sha256',safe.sha256)
        FROM sitecontent_assetbinding b JOIN sitecontent_mediaasset a ON a.id=b.asset_id
        LEFT JOIN sitecontent_mediaobjectversion v ON v.asset_id=a.id AND v.version=a.current_object_version
        LEFT JOIN sitecontent_mediavariant safe ON safe.asset_id=a.id AND safe.name='safe'
        WHERE b.site_id=%s AND b.record_id=%s AND a.site_id=%s
        ORDER BY b.field_key,b."order",b.asset_id""",
        (site_id, str(record_id), site_id),
    )
    bindings = [item[0] for item in cur.fetchall()]
    cur.execute(
        """SELECT jsonb_build_object('target_id',target_id,'field_key',field_key,
        'order',"order",'deletion_policy',deletion_policy,'target_type',target_type)
        FROM sitecontent_contentrelationship WHERE site_id=%s AND source_id=%s
        ORDER BY field_key,"order",target_id""",
        (site_id, str(record_id)),
    )
    return semantic_fingerprint(record, bindings, [item[0] for item in cur.fetchall()])


def subject(cur, *, site_id: str, record_id) -> dict | None:
    cur.execute(
        'SELECT to_jsonb(s) FROM sitecontent_reviewsubject s WHERE site_id=%s AND record_id=%s',
        (site_id, str(record_id)),
    )
    row = cur.fetchone()
    return row[0] if row else None


def ensure_subject(cur, *, site_id: str, record_id) -> dict:
    current = subject(cur, site_id=site_id, record_id=record_id)
    if current:
        return current
    # Recover only unambiguous original create provenance; transition actors are not authors.
    cur.execute(
        """SELECT DISTINCT actor_ref FROM sitecontent_workspaceauditevent
                   WHERE site_id=%s AND object_ref=%s AND action='content.create' """,
        (site_id, str(record_id)),
    )
    actors = [row[0] for row in cur.fetchall()]
    creator = None
    if len(actors) == 1 and actors[0].startswith('user:'):
        with suppress(ValueError):
            creator = str(UUID(actors[0][5:]))
    cur.execute(
        """INSERT INTO sitecontent_reviewsubject
        (id,site_id,record_id,schema_version,original_creator_id,semantic_author_id,adopted_snapshot,
         semantic_revision,semantic_generation,fingerprint,created_at,updated_at)
         VALUES (%s,%s,%s,1,%s,NULL,false,%s,1,%s,NOW(),NOW()) ON CONFLICT(record_id) DO NOTHING""",
        (str(uuid4()), site_id, str(record_id), creator, str(uuid4()), '0' * 64),
    )
    created = subject(cur, site_id=site_id, record_id=record_id)
    if created is None:
        raise ValueError('content_review_subject_unavailable')
    return created


def prepare_transition(
    cur, *, site_id: str, record_id, actor_ref: str, destination: str, policy: dict
):
    actor = str(UUID(actor_ref.removeprefix('user:')))
    permission = (
        'publish'
        if destination == 'published'
        else 'schedule'
        if destination == 'scheduled'
        else 'write'
    )
    member(cur, site_id=site_id, user_id=actor, permission=permission, lock=True)
    if destination in {'published', 'scheduled'} and policy['require_review']:
        cur.execute(
            'SELECT base2_workspace_approval_valid(%s,%s,%s,%s)',
            (site_id, str(record_id), actor, permission),
        )
        if not cur.fetchone()[0]:
            raise ValueError('content_review_required')
    if destination == 'in_review':
        current = ensure_subject(cur, site_id=site_id, record_id=record_id)
        if policy['require_review'] and (
            not current['semantic_author_id']
            or not (current['original_creator_id'] or current['adopted_snapshot'])
        ):
            raise ValueError('content_review_authorship_unknown')
        excluded = [
            value
            for value in (current['original_creator_id'], current['semantic_author_id'], actor)
            if value
        ]
        if not policy['require_review']:
            excluded = [actor]
        cur.execute('SELECT * FROM base2_workspace_reviewers(%s,%s::uuid[])', (site_id, excluded))
        reviewers = cur.fetchall()
        if policy['require_review'] and not reviewers:
            raise ValueError('content_review_no_independent_reviewer')
        fingerprint = current_fingerprint(cur, site_id=site_id, record_id=record_id)
        submission = str(uuid4())
        revision = str(uuid4())
        cur.execute(
            """UPDATE sitecontent_reviewsubject SET fingerprint=%s,submitter_id=%s,
            submission_id=%s,semantic_revision=%s,submitted_at=NOW(),scheduled_by_id=NULL,schedule_policy_version=NULL,
            updated_at=NOW() WHERE record_id=%s AND site_id=%s""",
            (fingerprint, actor, submission, revision, str(record_id), site_id),
        )
        for row in reviewers:
            cur.execute(
                """INSERT INTO sitecontent_reviewnotificationintent
                (id,site_id,record_id,submission_id,subject_revision,recipient_id,channel,event,status,
                 attempts,available_at,last_error_code,created_at,updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,'email','review_requested','pending',0,NOW(),'',NOW(),NOW())
                ON CONFLICT(site_id,submission_id,recipient_id,channel) DO NOTHING""",
                (
                    str(uuid4()),
                    site_id,
                    str(record_id),
                    submission,
                    revision,
                    str(row[0]),
                ),
            )
        audit(
            cur,
            site_id=site_id,
            actor_ref=actor_ref,
            object_ref=str(record_id),
            action='content.review_requested',
        )
    elif destination == 'scheduled':
        ensure_subject(cur, site_id=site_id, record_id=record_id)
        cur.execute(
            """UPDATE sitecontent_reviewsubject SET scheduled_by_id=%s,schedule_policy_version=%s,
                       updated_at=NOW() WHERE record_id=%s AND site_id=%s""",
            (actor, policy['version'] or None, str(record_id), site_id),
        )
    elif destination in {'draft', 'archived', 'deleted'}:
        cur.execute(
            """UPDATE sitecontent_reviewsubject SET submission_id=NULL,submitted_at=NULL,
            submitter_id=NULL,scheduled_by_id=NULL,schedule_policy_version=NULL,updated_at=NOW()
            WHERE record_id=%s AND site_id=%s""",
            (str(record_id), site_id),
        )


def review_action(
    *, site_id: str, type_key: str, record_id, user_id, expected_version: int, adopt: bool = False
) -> dict:
    actor = f'user:{user_id}'
    with workspace_db_conn(tenant_id=site_id) as conn:
        try:
            with conn.cursor() as cur:
                begin_effect(cur, actor_ref=actor)
                policy = read_policy(cur, site_id=site_id, lock=True)
                cur.execute(
                    """SELECT version,state FROM sitecontent_contentrecord WHERE site_id=%s
                    AND id=%s AND content_type=%s AND deleted_at IS NULL FOR UPDATE""",
                    (site_id, str(record_id), type_key),
                )
                record = cur.fetchone()
                if not record:
                    raise ValueError('content_not_found')
                if record[0] != expected_version:
                    raise ValueError('content_version_conflict')
                member(
                    cur,
                    site_id=site_id,
                    user_id=user_id,
                    permission='write' if adopt else 'review',
                    lock=True,
                )
                current = ensure_subject(cur, site_id=site_id, record_id=record_id)
                fingerprint = current_fingerprint(cur, site_id=site_id, record_id=record_id)
                if adopt:
                    cur.execute(
                        """UPDATE sitecontent_reviewsubject SET adopted_snapshot=true,semantic_author_id=%s,
                        semantic_revision=%s,semantic_generation=semantic_generation+1,fingerprint=%s,
                        submitter_id=NULL,submission_id=NULL,submitted_at=NULL,scheduled_by_id=NULL,
                        schedule_policy_version=NULL,updated_at=NOW() WHERE site_id=%s AND record_id=%s""",
                        (str(user_id), str(uuid4()), fingerprint, site_id, str(record_id)),
                    )
                    cur.execute(
                        """UPDATE sitecontent_contentrecord SET state='draft',publish_at=NULL,
                        schedule_timezone='',version=version+1,updated_at=NOW() WHERE id=%s AND site_id=%s""",
                        (str(record_id), site_id),
                    )
                    action = 'content.review_subject_adopted'
                else:
                    if record[1] != 'in_review' or not review_is_independent(current, str(user_id)):
                        raise ValueError('content_review_independent_reviewer_required')
                    if current['fingerprint'] != fingerprint or not current['submission_id']:
                        raise ValueError('content_review_stale')
                    if policy['version'] < 1:
                        raise ValueError('workspace_policy_unavailable')
                    cur.execute(
                        """INSERT INTO sitecontent_reviewapproval
                        (id,site_id,record_id,subject_revision,semantic_generation,fingerprint,policy_version,
                         reviewer_id,approved_at,created_at,updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),NOW()) ON CONFLICT DO NOTHING""",
                        (
                            str(uuid4()),
                            site_id,
                            str(record_id),
                            current['semantic_revision'],
                            current['semantic_generation'],
                            fingerprint,
                            policy['version'],
                            str(user_id),
                        ),
                    )
                    action = 'content.review_approved'
                audit(
                    cur, site_id=site_id, actor_ref=actor, object_ref=str(record_id), action=action
                )
            conn.commit()
            return {
                'record_id': str(record_id),
                'version': record[0] + int(adopt),
                'state': 'draft' if adopt else record[1],
                'review_status': 'draft' if adopt else 'approved',
            }
        except Exception:
            conn.rollback()
            raise


def authorize_scheduled(cur, *, site_id: str, record_id, policy: dict) -> bool:
    current = subject(cur, site_id=site_id, record_id=record_id)
    if not current or not current['scheduled_by_id']:
        return False
    try:
        member(
            cur,
            site_id=site_id,
            user_id=current['scheduled_by_id'],
            permission='schedule',
            lock=True,
        )
    except PermissionError:
        return False
    if current['schedule_policy_version'] != (policy['version'] or None):
        return False
    if policy['require_review']:
        if current['fingerprint'] != current_fingerprint(cur, site_id=site_id, record_id=record_id):
            return False
        cur.execute(
            'SELECT base2_workspace_approval_valid(%s,%s,%s,%s)',
            (site_id, str(record_id), current['scheduled_by_id'], 'schedule'),
        )
        return bool(cur.fetchone()[0])
    return True


def authorize_read(cur, *, site_id: str, requester_ref: str) -> dict:
    user_id = UUID(requester_ref.removeprefix('user:'))
    return member(cur, site_id=site_id, user_id=user_id, permission='read', lock=True)


def review_metadata(*, site_id: str, record_id, user_id) -> dict:
    with workspace_db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
        begin_effect(cur)
        policy = read_policy(cur, site_id=site_id, lock=True)
        cur.execute(
            """SELECT r.state,w.transitions FROM sitecontent_contentrecord r
            JOIN sitecontent_workflowdefinition w ON w.definition_id=r.definition_id
            WHERE r.id=%s AND r.site_id=%s AND r.deleted_at IS NULL""",
            (str(record_id), site_id),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError('content_not_found')
        membership = member(cur, site_id=site_id, user_id=user_id, permission='read')
        role = membership['role']
        current = subject(cur, site_id=site_id, record_id=record_id)
        approved = False
        if current and policy['version']:
            cur.execute(
                'SELECT base2_workspace_approval_valid(%s,%s,%s,%s)',
                (
                    site_id,
                    str(record_id),
                    str(user_id),
                    'read',
                ),
            )
            approved = bool(cur.fetchone()[0])
        unknown = (
            not current
            or not current['semantic_author_id']
            or not (current['original_creator_id'] or current['adopted_snapshot'])
        )
        recovery_reason = None
        if (
            policy['require_review']
            and current
            and row[0] == 'in_review'
            and not approved
            and not unknown
        ):
            excluded = [
                value
                for value in (
                    current['original_creator_id'],
                    current['semantic_author_id'],
                    current['submitter_id'],
                )
                if value
            ]
            cur.execute(
                'SELECT * FROM base2_workspace_reviewers(%s,%s::uuid[])', (site_id, excluded)
            )
            if not cur.fetchall():
                recovery_reason = 'no_independent_reviewer'
        actions = []
        for transition in row[1]:
            action = transition.get('action')
            if row[0] not in transition.get('from', []) or role not in {'owner', 'admin', 'editor'}:
                continue
            if action in {'publish', 'delete'} and role not in {'owner', 'admin'}:
                continue
            if action in {'publish', 'schedule'} and policy['require_review'] and not approved:
                continue
            if action == 'submit_review' and policy['require_review'] and unknown:
                continue
            actions.append(action)
        if role in {'owner', 'admin', 'editor'}:
            actions.append('adopt_review_subject')
        if (
            current
            and row[0] == 'in_review'
            and role in {'owner', 'admin'}
            and review_is_independent(current, str(user_id))
        ):
            actions.append('approve_review')
        return {
            'allowedActions': sorted(set(actions)),
            'review': {
                'status': 'authorship_unknown'
                if unknown
                else 'approved'
                if approved
                else 'pending'
                if row[0] == 'in_review'
                else 'not_requested',
                'requiresReview': policy['require_review'],
                'policyVersion': policy['version'],
                'semanticRevision': current['semantic_revision'] if current else None,
                'deliveryAdapter': 'local_test',
                'recoveryReason': recovery_reason,
            },
        }
