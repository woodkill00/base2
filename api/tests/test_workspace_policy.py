"""Shared policy and immutable review decision regressions."""

from copy import deepcopy
from contextlib import contextmanager
from uuid import UUID
from api.repositories import workspace_policy as repo

import pytest


def test_fingerprint_covers_all_publication_fields_not_state():
    from api.repositories.workspace_policy import semantic_fingerprint

    record = {
        'title': 'One',
        'slug': 'one',
        'body': 'Body',
        'excerpt': 'Excerpt',
        'metadata': {},
        'values': {},
        'schema_version': 1,
        'definition_id': 'definition',
        'content_type': 'article',
        'sitemap_include': True,
        'search_visible': True,
    }
    original = semantic_fingerprint(record, [], [])
    for key in record:
        changed = deepcopy(record)
        changed[key] = str(record[key]) + '-changed'
        assert semantic_fingerprint(changed, [], []) != original, key
    assert (
        semantic_fingerprint(
            {**record, 'state': 'published', 'version': 3, 'publish_at': 'now'}, [], []
        )
        == original
    )
    assert semantic_fingerprint(record, [{'id': 'asset', 'sha256': 'a'}], []) != original
    assert semantic_fingerprint(record, [], [{'target': 'other'}]) != original


def test_review_is_not_a_state_alias_and_excludes_all_human_authors():
    from api.repositories.workspace_policy import review_is_independent

    subject = {
        'original_creator_id': 'creator',
        'semantic_author_id': 'editor',
        'submitter_id': 'submitter',
        'adopted_snapshot': False,
    }
    for actor in ('creator', 'editor', 'submitter'):
        assert not review_is_independent(subject, actor)
    assert review_is_independent(subject, 'reviewer')
    subject['original_creator_id'] = None
    assert not review_is_independent(subject, 'reviewer')
    subject['adopted_snapshot'] = True
    assert review_is_independent(subject, 'reviewer')
    subject['semantic_author_id'] = None
    assert not review_is_independent(subject, 'reviewer')


def test_policy_update_is_closed_and_requires_both_fields():
    from api.routes.settings import WorkspacePolicyUpdate
    from pydantic import ValidationError

    good = {'expected_version': 0, 'require_review': True, 'public_access': 'members_only'}
    assert WorkspacePolicyUpdate(**good).require_review is True
    for changes in (
        {'tenant_id': 'other'},
        {'require_review': 'false'},
        {'public_access': 'everyone'},
        {'expected_version': True},
    ):
        with pytest.raises(ValidationError):
            WorkspacePolicyUpdate(**{**good, **changes})


ACTOR = UUID(int=11)
ORG = UUID(int=22)
RECORD = UUID(int=33)


class PolicyCursor:
    def __init__(self, *, version=1, allowed=True, approved=True):
        self.version, self.allowed, self.approved = version, allowed, approved
        self.calls = []
        self.sql = ''
        self.state = 'in_review'
        self.fail_audit = False
        self.subject = {
            'semantic_author_id': str(UUID(int=1)),
            'original_creator_id': str(UUID(int=1)),
            'submitter_id': str(UUID(int=1)),
            'adopted_snapshot': False,
            'semantic_revision': str(UUID(int=2)),
            'semantic_generation': 1,
            'submission_id': str(UUID(int=3)),
            'fingerprint': 'f' * 64,
            'scheduled_by_id': str(ACTOR),
            'schedule_policy_version': version,
        }

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        self.sql = ' '.join(sql.split())
        self.calls.append((self.sql, params))
        if self.fail_audit and 'INSERT INTO sitecontent_workspaceauditevent' in self.sql:
            raise RuntimeError('audit_down')

    def fetchone(self):
        if 'base2_workspace_member' in self.sql:
            return (ORG, 'admin') if self.allowed else None
        if 'SELECT schema_version' in self.sql:
            return (
                (1, self.version, True, 'members_only', ORG, 'explicit') if self.version else None
            )
        if 'RETURNING version' in self.sql:
            return (self.version + 1,)
        if 'SELECT version,state' in self.sql:
            return (2, self.state)
        if 'SELECT to_jsonb(s)' in self.sql:
            return (self.subject,)
        if 'approval_valid' in self.sql:
            return (self.approved,)
        if 'SELECT r.state' in self.sql:
            return self.state, [
                {'action': action, 'from': ['in_review']}
                for action in ['publish', 'schedule', 'return_draft']
            ]
        return None

    def fetchall(self):
        return [(UUID(int=44),)] if 'base2_workspace_reviewers' in self.sql else []


class PolicyConnection:
    def __init__(self, cur):
        self.cur, self.commits, self.rollbacks = cur, 0, 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def policy_connection(monkeypatch, cur):
    conn = PolicyConnection(cur)

    @contextmanager
    def connection(*, tenant_id):
        assert tenant_id == 'site-a'
        yield conn

    monkeypatch.setattr(repo, 'workspace_db_conn', connection)
    monkeypatch.setattr(repo, 'current_fingerprint', lambda *args, **kwargs: 'f' * 64)
    return conn


def test_policy_default_get_is_conservative_and_server_scoped(monkeypatch):
    policy_connection(monkeypatch, PolicyCursor(version=0))
    result = repo.get_policy(site_id='site-a', user_id=ACTOR)
    assert result['version'] == 0 and result['require_review'] is True
    assert result['public_access'] == 'members_only'
    assert result['scope'] == {'site_id': 'site-a', 'organization_id': str(ORG)}
    assert result['provenance'] == 'default'


@pytest.mark.parametrize('version,expected,success', [(0, 0, True), (1, 1, True), (2, 1, False)])
def test_policy_cas_audit_and_lock_order(monkeypatch, version, expected, success):
    cur = PolicyCursor(version=version)
    conn = policy_connection(monkeypatch, cur)
    result = repo.update_policy(
        site_id='site-a',
        user_id=ACTOR,
        expected_version=expected,
        require_review=True,
        public_access='members_only',
    )
    assert (result is not None) == success
    assert conn.commits == int(success)
    assert 'pg_advisory_xact_lock' in cur.calls[0][0]
    if success:
        assert result['version'] == version + 1
        assert any('workspaceauditevent' in sql for sql, _ in cur.calls)
    else:
        assert not any(
            'INSERT' in sql or 'UPDATE sitecontent_workspacepolicy' in sql for sql, _ in cur.calls
        )


def test_policy_missing_membership_and_audit_failure_never_commit(monkeypatch):
    cur = PolicyCursor(allowed=False)
    conn = policy_connection(monkeypatch, cur)
    with pytest.raises(PermissionError):
        repo.update_policy(
            site_id='site-a',
            user_id=ACTOR,
            expected_version=1,
            require_review=True,
            public_access='members_only',
        )
    assert conn.commits == 0 and conn.rollbacks == 1
    cur.allowed = True
    cur.fail_audit = True
    with pytest.raises(RuntimeError, match='audit_down'):
        repo.update_policy(
            site_id='site-a',
            user_id=ACTOR,
            expected_version=1,
            require_review=True,
            public_access='members_only',
        )
    assert conn.commits == 0 and conn.rollbacks == 2


def test_unverified_remote_transport_blocks_restrictive_activation_before_db(monkeypatch):
    monkeypatch.setattr(repo.settings, 'CONTENT_WORKSPACE_STORAGE_BACKEND', 's3')
    monkeypatch.setattr(repo, 'workspace_db_conn', lambda **kwargs: pytest.fail('DB mutation'))
    with pytest.raises(ValueError, match='storage_transport_unverified'):
        repo.update_policy(
            site_id='site-a',
            user_id=ACTOR,
            expected_version=1,
            require_review=False,
            public_access='members_only',
        )


def test_approval_is_separate_immutable_action_not_a_publication(monkeypatch):
    cur = PolicyCursor()
    conn = policy_connection(monkeypatch, cur)
    result = repo.review_action(
        site_id='site-a', type_key='article', record_id=RECORD, user_id=ACTOR, expected_version=2
    )
    assert result['state'] == 'in_review' and result['review_status'] == 'approved'
    assert any('INSERT INTO sitecontent_reviewapproval' in sql for sql, _ in cur.calls)
    assert not any('UPDATE sitecontent_contentrecord' in sql for sql, _ in cur.calls)
    assert conn.commits == 1


@pytest.mark.parametrize(
    'change,code',
    [
        ({'semantic_author_id': str(ACTOR)}, 'independent_reviewer'),
        ({'original_creator_id': None}, 'independent_reviewer'),
        ({'fingerprint': 'a' * 64}, 'stale'),
        ({'submission_id': None}, 'stale'),
    ],
)
def test_approval_rejects_authorship_and_revision_bypass(monkeypatch, change, code):
    cur = PolicyCursor()
    cur.subject.update(change)
    conn = policy_connection(monkeypatch, cur)
    with pytest.raises(ValueError, match=code):
        repo.review_action(
            site_id='site-a',
            type_key='article',
            record_id=RECORD,
            user_id=ACTOR,
            expected_version=2,
        )
    assert conn.commits == 0


def test_explicit_adoption_changes_subject_and_drafts_without_approval(monkeypatch):
    cur = PolicyCursor()
    cur.subject['original_creator_id'] = None
    conn = policy_connection(monkeypatch, cur)
    result = repo.review_action(
        site_id='site-a',
        type_key='article',
        record_id=RECORD,
        user_id=ACTOR,
        expected_version=2,
        adopt=True,
    )
    assert result['state'] == 'draft' and result['version'] == 3
    assert any('semantic_generation=semantic_generation+1' in sql for sql, _ in cur.calls)
    assert not any('INSERT INTO sitecontent_reviewapproval' in sql for sql, _ in cur.calls)
    assert conn.commits == 1


def test_stale_action_does_not_adopt_or_approve(monkeypatch):
    cur = PolicyCursor()
    conn = policy_connection(monkeypatch, cur)
    with pytest.raises(ValueError, match='content_version_conflict'):
        repo.review_action(
            site_id='site-a',
            type_key='article',
            record_id=RECORD,
            user_id=ACTOR,
            expected_version=1,
        )
    assert conn.commits == 0


def test_allowed_actions_do_not_offer_publish_without_review(monkeypatch):
    cur = PolicyCursor(approved=False)
    policy_connection(monkeypatch, cur)
    result = repo.review_metadata(site_id='site-a', record_id=RECORD, user_id=ACTOR)
    assert 'publish' not in result['allowedActions'] and 'schedule' not in result['allowedActions']
    assert 'approve_review' in result['allowedActions']
    assert result['review']['status'] == 'pending'


def test_policy_endpoints_preserve_shape_and_fail_closed(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from api.main import app
    from api.routes import settings as routes

    monkeypatch.setattr(
        routes, '_policy_scope', lambda request: (SimpleNamespace(user_id=ACTOR), 'site-a')
    )
    snapshot = {
        'schema_version': 1,
        'version': 2,
        'require_review': True,
        'public_access': 'members_only',
        'scope': {'site_id': 'site-a', 'organization_id': str(ORG)},
        'provenance': 'explicit',
        'permissions': {'read': True, 'write': True},
        'restrictions': [],
    }
    monkeypatch.setattr(routes.workspace_policy, 'get_policy', lambda **kwargs: snapshot)
    client = TestClient(app)
    got = client.get('/api/settings/workspace-policy')
    assert got.status_code == 200 and got.json() == snapshot
    assert got.headers['cache-control'] == 'private, no-store'
    monkeypatch.setattr(routes.workspace_policy, 'update_policy', lambda **kwargs: None)
    body = {'expected_version': 1, 'require_review': True, 'public_access': 'members_only'}
    assert client.put('/api/settings/workspace-policy', json=body).status_code == 409
    assert (
        client.put(
            '/api/settings/workspace-policy', json={**body, 'organization_id': str(ORG)}
        ).status_code
        == 422
    )

    def denied(**kwargs):
        raise PermissionError('denied')

    monkeypatch.setattr(routes.workspace_policy, 'update_policy', denied)
    assert client.put('/api/settings/workspace-policy', json=body).status_code == 404

    def unavailable(**kwargs):
        raise RuntimeError('db_down')

    monkeypatch.setattr(routes.workspace_policy, 'get_policy', unavailable)
    assert client.get('/api/settings/workspace-policy').status_code == 503


@pytest.mark.parametrize('destination', ['published', 'scheduled', 'draft', 'archived', 'deleted'])
def test_transition_rechecks_current_authority_and_clears_or_preserves_cycle(
    monkeypatch, destination
):
    cur = PolicyCursor()
    policy_connection(monkeypatch, cur)
    repo.prepare_transition(
        cur,
        site_id='site-a',
        record_id=RECORD,
        actor_ref=f'user:{ACTOR}',
        destination=destination,
        policy={'version': 1, 'require_review': True},
    )
    assert cur.calls[0][1][-2:] == (
        'publish'
        if destination == 'published'
        else 'schedule'
        if destination == 'scheduled'
        else 'write',
        True,
    )
    statements = ' '.join(sql for sql, _ in cur.calls)
    if destination in {'draft', 'archived', 'deleted'}:
        assert 'submission_id=NULL' in statements
    elif destination == 'scheduled':
        assert 'scheduled_by_id=%s' in statements
    if destination in {'published', 'scheduled'}:
        cur.approved = False
        with pytest.raises(ValueError, match='content_review_required'):
            repo.prepare_transition(
                cur,
                site_id='site-a',
                record_id=RECORD,
                actor_ref=f'user:{ACTOR}',
                destination=destination,
                policy={'version': 1, 'require_review': True},
            )


def test_submission_new_cycle_is_shared_by_all_durable_recipient_intents(monkeypatch):
    class Reviewers(PolicyCursor):
        def fetchall(self):
            return (
                [(UUID(int=44),), (UUID(int=55),)]
                if 'base2_workspace_reviewers' in self.sql
                else []
            )

    cur = Reviewers()
    policy_connection(monkeypatch, cur)
    for _ in range(2):
        repo.prepare_transition(
            cur,
            site_id='site-a',
            record_id=RECORD,
            actor_ref=f'user:{ACTOR}',
            destination='in_review',
            policy={'version': 1, 'require_review': True},
        )
    updates = [
        params for sql, params in cur.calls if sql.startswith('UPDATE sitecontent_reviewsubject')
    ]
    intents = [
        params
        for sql, params in cur.calls
        if 'INSERT INTO sitecontent_reviewnotificationintent' in sql
    ]
    assert updates[0][2:4] != updates[1][2:4]
    assert all(item[3:5] == updates[index // 2][2:4] for index, item in enumerate(intents))
    assert updates[0][3] != cur.subject['semantic_revision']
    assert all('semantic_generation=' not in sql for sql, _ in cur.calls)
    cur.subject['semantic_author_id'] = None
    with pytest.raises(ValueError, match='authorship_unknown'):
        repo.prepare_transition(
            cur,
            site_id='site-a',
            record_id=RECORD,
            actor_ref=f'user:{ACTOR}',
            destination='in_review',
            policy={'version': 1, 'require_review': True},
        )


def test_live_fingerprint_load_covers_bindings_and_relationships():
    class Fingerprint(PolicyCursor):
        exists = True

        def fetchone(self):
            return ({'title': 'Synthetic'},) if self.exists else None

        def fetchall(self):
            return (
                [({'sha256': 'a' * 64},)]
                if 'assetbinding' in self.sql
                else [({'target_id': 'other'},)]
            )

    cur = Fingerprint()
    assert repo.current_fingerprint(
        cur, site_id='site-a', record_id=RECORD
    ) == repo.semantic_fingerprint(
        {'title': 'Synthetic'}, [{'sha256': 'a' * 64}], [{'target_id': 'other'}]
    )
    cur.exists = False
    with pytest.raises(ValueError, match='content_not_found'):
        repo.current_fingerprint(cur, site_id='site-a', record_id=RECORD)


@pytest.mark.parametrize(
    'provenance',
    [
        [],
        [(f'user:{ACTOR}',)],
        [('system:import-worker',)],
        [(f'user:{ACTOR}',), (f'user:{UUID(int=9)}',)],
    ],
)
def test_historical_subject_never_invents_current_author(provenance):
    class Historical(PolicyCursor):
        inserted = False

        def execute(self, sql, params=()):
            super().execute(sql, params)
            if 'INSERT INTO sitecontent_reviewsubject' in sql:
                self.inserted = True

        def fetchone(self):
            return (self.subject,) if self.inserted else None

        def fetchall(self):
            return provenance

    cur = Historical()
    assert repo.ensure_subject(cur, site_id='site-a', record_id=RECORD) == cur.subject
    sql, params = next(
        (sql, params) for sql, params in cur.calls if 'INSERT INTO sitecontent_reviewsubject' in sql
    )
    assert 'NULL,false' in sql
    assert params[3] == (str(ACTOR) if provenance == [(f'user:{ACTOR}',)] else None)


@pytest.mark.parametrize(
    'case',
    [
        'valid',
        'missing',
        'no_scheduler',
        'revoked',
        'policy_changed',
        'fingerprint_changed',
        'unapproved',
        'not_required',
    ],
)
def test_due_scheduler_rechecks_every_authority_boundary(monkeypatch, case):
    cur = PolicyCursor()
    policy_connection(monkeypatch, cur)
    p = {'version': 1, 'require_review': case != 'not_required'}
    if case == 'missing':
        cur.subject = None
    elif case == 'no_scheduler':
        cur.subject['scheduled_by_id'] = None
    elif case == 'revoked':
        cur.allowed = False
    elif case == 'policy_changed':
        p['version'] = 2
    elif case == 'fingerprint_changed':
        cur.subject['fingerprint'] = 'a' * 64
    elif case == 'unapproved':
        cur.approved = False
    assert repo.authorize_scheduled(cur, site_id='site-a', record_id=RECORD, policy=p) == (
        case in {'valid', 'not_required'}
    )
    if case == 'valid':
        assert (
            repo.authorize_read(cur, site_id='site-a', requester_ref=f'user:{ACTOR}')['role']
            == 'admin'
        )


def test_policy_schema_scope_and_transport_discovery_fail_closed(monkeypatch):
    class Future(PolicyCursor):
        def fetchone(self):
            return (2, 1, True, 'members_only', ORG, 'explicit')

    with pytest.raises(ValueError, match='schema_unsupported'):
        repo.read_policy(Future(), site_id='site-a')
    p = {'organization_id': str(ORG), 'version': 1}
    with pytest.raises(ValueError, match='scope_invalid'):
        repo._envelope(
            p, site_id='site-a', membership={'organization_id': str(ACTOR), 'role': 'admin'}
        )
    monkeypatch.setattr(repo.settings, 'CONTENT_WORKSPACE_STORAGE_BACKEND', 's3')
    result = repo._envelope(
        p, site_id='site-a', membership={'organization_id': str(ORG), 'role': 'viewer'}
    )
    assert result['permissions']['write'] is False
    assert result['restrictions'] == ['storage_transport_unverified']


def test_policy_first_insert_loser_rolls_back_without_audit(monkeypatch):
    class Loser(PolicyCursor):
        def fetchone(self):
            return None if 'RETURNING version' in self.sql else super().fetchone()

    cur = Loser(version=0)
    conn = policy_connection(monkeypatch, cur)
    assert (
        repo.update_policy(
            site_id='site-a',
            user_id=ACTOR,
            expected_version=0,
            require_review=True,
            public_access='members_only',
        )
        is None
    )
    assert conn.rollbacks == 1 and conn.commits == 0
    assert not any('workspaceauditevent' in sql for sql, _ in cur.calls)


@pytest.mark.parametrize(
    'role,state,known',
    [
        ('viewer', 'in_review', True),
        ('editor', 'draft', True),
        ('admin', 'draft', False),
        ('admin', 'in_review', True),
    ],
)
def test_action_metadata_never_offers_unauthorized_or_unknown_author_publish(
    monkeypatch, role, state, known
):
    class Actions(PolicyCursor):
        def fetchone(self):
            if 'base2_workspace_member' in self.sql:
                return ORG, role
            if 'SELECT r.state' in self.sql:
                return state, [
                    {'action': a, 'from': ['draft', 'in_review']}
                    for a in ('publish', 'schedule', 'delete', 'submit_review')
                ] + [{'action': 'irrelevant', 'from': ['deleted']}]
            if 'SELECT to_jsonb(s)' in self.sql and not known:
                return None
            return super().fetchone()

    cur = Actions(approved=False)
    policy_connection(monkeypatch, cur)
    result = repo.review_metadata(site_id='site-a', record_id=RECORD, user_id=ACTOR)
    actions = result['allowedActions']
    assert 'publish' not in actions and 'schedule' not in actions and 'irrelevant' not in actions
    if role == 'viewer':
        assert actions == []
    if role == 'editor':
        assert 'delete' not in actions
    if not known:
        assert 'submit_review' not in actions and result['review']['status'] == 'authorship_unknown'
    if state == 'draft' and known:
        assert result['review']['status'] == 'not_requested'


@pytest.mark.parametrize('missing,version', [(True, 1), (False, 0)])
def test_approval_denies_missing_record_and_unpersisted_policy(monkeypatch, missing, version):
    class Missing(PolicyCursor):
        def fetchone(self):
            if missing and 'SELECT version,state' in self.sql:
                return None
            return super().fetchone()

    conn = policy_connection(monkeypatch, Missing(version=version))
    with pytest.raises(
        ValueError, match='content_not_found' if missing else 'workspace_policy_unavailable'
    ):
        repo.review_action(
            site_id='site-a',
            type_key='article',
            record_id=RECORD,
            user_id=ACTOR,
            expected_version=2,
        )
    assert conn.commits == 0 and conn.rollbacks == 1


@pytest.mark.parametrize('value', [False, 1, 'true', None])
def test_adoption_confirmation_requires_literal_boolean(value):
    from api.routes.content_workspace import ReviewSubjectRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ReviewSubjectRequest(expected_version=1, adopt_snapshot=value)


def test_unassigned_review_rejects_new_cycle_and_exposes_safe_recovery(monkeypatch):
    class Unassigned(PolicyCursor):
        def fetchall(self):
            return []

    cur = Unassigned(approved=False)
    policy_connection(monkeypatch, cur)
    with pytest.raises(ValueError, match='content_review_no_independent_reviewer'):
        repo.prepare_transition(
            cur,
            site_id='site-a',
            record_id=RECORD,
            actor_ref=f'user:{ACTOR}',
            destination='in_review',
            policy={'version': 1, 'require_review': True},
        )
    assert not any('UPDATE' in sql or 'INSERT' in sql for sql, _ in cur.calls)
    metadata = repo.review_metadata(site_id='site-a', record_id=RECORD, user_id=ACTOR)
    assert metadata['review']['status'] == 'pending'
    assert metadata['review']['recoveryReason'] == 'no_independent_reviewer'


@pytest.mark.parametrize('known,recipients', [(True, []), (False, []), (True, [(UUID(int=1),)])])
def test_optional_workflow_submission_does_not_impose_independent_approval(
    monkeypatch, known, recipients
):
    class Optional(PolicyCursor):
        def fetchall(self):
            return recipients if 'base2_workspace_reviewers' in self.sql else []

    cur = Optional()
    if not known:
        cur.subject.update(original_creator_id=None, semantic_author_id=None)
    policy_connection(monkeypatch, cur)
    repo.prepare_transition(
        cur,
        site_id='site-a',
        record_id=RECORD,
        actor_ref=f'user:{ACTOR}',
        destination='in_review',
        policy={'version': 1, 'require_review': False},
    )
    lookup = next(params for sql, params in cur.calls if 'base2_workspace_reviewers' in sql)
    assert lookup == ('site-a', [str(ACTOR)])
    assert len(
        [sql for sql, _ in cur.calls if 'INSERT INTO sitecontent_reviewnotificationintent' in sql]
    ) == len(recipients)
    assert any('UPDATE sitecontent_reviewsubject' in sql for sql, _ in cur.calls)


def test_optional_unknown_authorship_does_not_hide_submit_or_invent_recovery_requirement(
    monkeypatch,
):
    class Optional(PolicyCursor):
        def fetchone(self):
            if 'SELECT r.state' in self.sql:
                return 'draft', [{'action': 'submit_review', 'from': ['draft']}]
            return super().fetchone()

        def fetchall(self):
            return []

    cur = Optional(approved=False)
    cur.subject.update(original_creator_id=None, semantic_author_id=None)
    policy_connection(monkeypatch, cur)
    monkeypatch.setattr(
        repo, 'read_policy', lambda *a, **k: {'version': 1, 'require_review': False}
    )
    result = repo.review_metadata(site_id='site-a', record_id=RECORD, user_id=ACTOR)
    assert 'submit_review' in result['allowedActions']
    assert result['review']['recoveryReason'] is None


def test_locked_policy_read_uses_shared_advisory_not_mutation_privileges():
    class ReadOnlyCursor:
        def __init__(self):
            self.calls = []
        def execute(self, sql, params=()):
            self.calls.append((' '.join(sql.split()), params))
            assert 'FOR UPDATE' not in sql and 'FOR SHARE' not in sql
        def fetchone(self):
            return (1, 7, True, 'members_only', UUID(int=1), 'explicit')

    cursor = ReadOnlyCursor()
    assert repo.read_policy(cursor, site_id='site-a', lock=True)['version'] == 7
    assert "current_setting('transaction_isolation') <> 'read committed'" in cursor.calls[0][0]
    assert "ERRCODE='25000'" in cursor.calls[0][0]
    assert cursor.calls[1] == (
        'SELECT pg_advisory_xact_lock(hashtext(%s))', (repo.POLICY_LOCK,),
    )
    assert cursor.calls[2][1] == ('site-a',)
