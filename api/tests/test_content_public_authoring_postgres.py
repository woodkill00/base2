"""Restricted-role public-copy persistence; collect locally, run only disposable native CI.

The existing fixture owns synthetic identities, not runtime writes. All authored copy,
review, publication, restoration and indexing use production restricted-role helpers.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID

import pytest

from api.repositories import workspace_policy as policy
from api.repositories.site_content import PostgresSiteContentRepository
from api.services.content_workspace_worker import index_workspace_record, publish_scheduled_record

pytestmark = pytest.mark.integration
COPY = {
    'excerpt': 'Explicit public summary',
    'body': '<b>Literal publiccopytoken</b>\n\nSecond paragraph',
}
PRIVATE = 'privatevaluetokenmustnotappear'


def create_copy(f):
    repo = f['repo']
    definition = repo.create_definition(
        site_id=f['site_id'],
        actor_ref=f"user:{f['creator_id']}",
        payload={
            'type_key': 'copy-article',
            'name': 'Copy article',
            'fields': [
                {'field_key': 'summary', 'label': 'Private summary', 'field_kind': 'long_text'}
            ],
        },
    )
    repo.publish_definition(
        site_id=f['site_id'],
        type_key='copy-article',
        version=definition['version'],
        expected_lock_version=definition['lockVersion'],
        confirm_lossy=False,
        actor_ref=f"user:{f['reviewer_id']}",
    )
    return repo.create_record(
        site_id=f['site_id'],
        type_key='copy-article',
        actor_ref=f"user:{f['creator_id']}",
        payload={
            'slug': 'public-copy',
            'title': 'Public copy title',
            'values': {'summary': PRIVATE},
            'public_content': COPY,
        },
    )


def scope(f, r):
    return {'site_id': f['site_id'], 'type_key': r['typeKey'], 'record_id': UUID(r['id'])}


def transition(f, r, action, when=None):
    # The fixture creator is an editor: authors submit/schedule; an existing
    # independent admin publishes. Approval never grants a new role.
    actor = f['reviewer_id'] if action == 'publish' else f['creator_id']
    return f['repo'].transition_record(
        **scope(f, r),
        expected_version=r['version'],
        actor_ref=f'user:{actor}',
        action=action,
        publish_at=when,
        timezone='UTC' if when else None,
    )


def reviewed(f, r):
    r = transition(f, r, 'submit_review')
    policy.review_action(**scope(f, r), user_id=f['reviewer_id'], expected_version=r['version'])
    return r


def test_explicit_copy_visibility_search_edit_review_and_restore(workspace_policy_fixture):
    f = workspace_policy_fixture
    policy.update_policy(
        site_id=f['site_id'],
        user_id=f['reviewer_id'],
        expected_version=1,
        require_review=True,
        public_access='public_allowed',
    )
    r = create_copy(f)
    public = PostgresSiteContentRepository()
    assert r['publicContent'] == COPY
    assert (
        public.get_content(site_id=f['site_id'], content_type=r['typeKey'], slug=r['slug']) is None
    )
    r = transition(f, reviewed(f, r), 'publish')
    item = public.get_content(site_id=f['site_id'], content_type=r['typeKey'], slug=r['slug'])
    assert item['excerpt'] == COPY['excerpt'] and item['body'] == COPY['body']
    assert 'values' not in item and PRIVATE not in str(item) and item['metadata'] == {}
    assert (
        index_workspace_record(
            site_id=f['site_id'], record_id=UUID(r['id']), job_version=r['version']
        )
        == 'indexed'
    )
    assert public.search(site_id=f['site_id'], query='publiccopytoken', limit=25, cursor=None)[
        'items'
    ]
    assert public.search(site_id=f['site_id'], query=PRIVATE, limit=25, cursor=None)['items'] == []
    old = r
    r = f['repo'].update_record(
        **scope(f, r),
        expected_version=r['version'],
        actor_ref=f"user:{f['creator_id']}",
        values=r['values'],
        public_content={'excerpt': 'Changed', 'body': 'Changed public copy'},
    )
    assert r['state'] == 'draft' and r['values'] == {'summary': PRIVATE}
    assert (
        public.get_content(site_id=f['site_id'], content_type=r['typeKey'], slug=r['slug']) is None
    )
    assert (
        public.search(site_id=f['site_id'], query='publiccopytoken', limit=25, cursor=None)['items']
        == []
    )
    with pytest.raises(ValueError, match='content_version_conflict'):
        f['repo'].update_record(
            **scope(f, r),
            expected_version=old['version'],
            actor_ref=f"user:{f['creator_id']}",
            values=r['values'],
            public_content=COPY,
        )
    # Old approval cannot authorize publication of the newly authored subject.
    pending = transition(f, r, 'submit_review')
    with pytest.raises(ValueError, match='review_required'):
        transition(f, pending, 'publish')
    policy.review_action(
        **scope(f, pending), user_id=f['reviewer_id'], expected_version=pending['version']
    )
    r = transition(f, pending, 'publish')
    restored = f['repo'].restore_record(
        **scope(f, r), version=1, expected_version=r['version'], actor_ref=f"user:{f['creator_id']}"
    )
    assert restored['publicContent'] == COPY and restored['state'] == 'draft'
    assert restored['restoration'] == {'sourceVersion': 1, 'publicContent': 'restored'}
    history = f['repo'].list_versions(**scope(f, r))['items']
    assert all(item['publicContentRestoreMode'] == 'snapshot' for item in history)


def test_clear_omission_stale_role_and_tenant_denials(workspace_policy_fixture):
    f = workspace_policy_fixture
    r = create_copy(f)
    r = f['repo'].update_record(
        **scope(f, r), expected_version=1, actor_ref=f"user:{f['creator_id']}", values=r['values']
    )
    assert r['publicContent'] == COPY
    r = f['repo'].update_record(
        **scope(f, r),
        expected_version=2,
        actor_ref=f"user:{f['creator_id']}",
        values=r['values'],
        public_content={'excerpt': '', 'body': ''},
    )
    assert r['publicContent'] == {'excerpt': '', 'body': ''}
    before = f['repo'].list_versions(**scope(f, r))
    f['execute'](
        "UPDATE api_identity_memberships SET role='viewer' WHERE user_id=%s",
        (str(f['creator_id']),),
    )
    with pytest.raises(PermissionError, match='workspace_policy_forbidden'):
        f['repo'].update_record(
            **scope(f, r),
            expected_version=r['version'],
            actor_ref=f"user:{f['creator_id']}",
            values=r['values'],
            public_content=COPY,
        )
    with pytest.raises(ValueError):
        f['repo'].get_record(**{**scope(f, r), 'site_id': 'other-site'})
    assert f['repo'].get_record(**scope(f, r))['publicContent'] == {'excerpt': '', 'body': ''}
    assert f['repo'].list_versions(**scope(f, r)) == before


def test_concurrent_public_copy_cas_has_one_complete_winner(workspace_policy_fixture):
    f = workspace_policy_fixture
    r = create_copy(f)
    barrier = Barrier(2)

    def write(label):
        barrier.wait()
        try:
            return f['repo'].update_record(
                **scope(f, r),
                expected_version=1,
                actor_ref=f"user:{f['creator_id']}",
                values={'summary': PRIVATE + label},
                public_content={'excerpt': label, 'body': label},
            )
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, ['first', 'second']))
    assert outcomes.count('content_version_conflict') == 1
    winner = next(item for item in outcomes if isinstance(item, dict))
    assert winner['publicContent']['excerpt'] == winner['publicContent']['body']
    assert winner['values']['summary'] == PRIVATE + winner['publicContent']['body']
    assert len(f['repo'].list_versions(**scope(f, r))['items']) == 1


def test_due_publication_snapshot_restores_copy_without_restoring_schedule(
    workspace_policy_fixture,
):
    f = workspace_policy_fixture
    r = create_copy(f)
    r = transition(f, reviewed(f, r), 'schedule', datetime.now(UTC) - timedelta(seconds=1))
    scheduled_version = r['version']
    assert publish_scheduled_record(site_id=f['site_id'], record_id=UUID(r['id'])) == 'published'
    r = f['repo'].get_record(**scope(f, r))
    r = f['repo'].update_record(
        **scope(f, r),
        expected_version=r['version'],
        actor_ref=f"user:{f['creator_id']}",
        values=r['values'],
        public_content={'excerpt': 'changed', 'body': 'changed'},
    )
    r = f['repo'].restore_record(
        **scope(f, r),
        version=scheduled_version,
        expected_version=r['version'],
        actor_ref=f"user:{f['creator_id']}",
    )
    assert r['publicContent'] == COPY and r['state'] == 'draft'
    persisted = f['execute'](
        'SELECT publish_at,schedule_timezone FROM sitecontent_contentrecord WHERE id=%s', (r['id'],)
    )[0]
    assert persisted == (None, '')


def test_import_update_history_restores_public_copy_without_import_authoring(
    workspace_policy_fixture, tmp_path, monkeypatch
):
    import hashlib
    import json
    from api.services.content_workspace_storage import PrivateArtifactStore
    from api.services.content_workspace_worker import validate_import_job, process_import_commit

    from api.settings import settings

    # Isolated deterministic test configuration, not a production credential or
    # a bypass: the real CursorCodec still signs and validates scoped grants.
    monkeypatch.setattr(settings, 'TOKEN_PEPPER', 'synthetic-public-copy-import-cursor-key-124')
    f = workspace_policy_fixture
    r = create_copy(f)
    store = PrivateArtifactStore(tmp_path / 'private', key=b'p' * 32, max_bytes=10000)
    content = json.dumps(
        [{'slug': r['slug'], 'title': 'Imported private update', 'summary': 'Imported private'}]
    ).encode()
    requester = f"user:{f['creator_id']}"
    job = f['repo'].create_import(
        site_id=f['site_id'],
        type_key=r['typeKey'],
        requester_ref=requester,
        idempotency_key='public-copy-history-import',
        payload={
            'format': 'json',
            'schema_version': 1,
            'source_sha256': hashlib.sha256(content).hexdigest(),
            'mapping': {},
            'duplicate_policy': 'update_exact',
            'atomic_policy': 'all_or_nothing',
        },
    )
    args = {
        'site_id': f['site_id'],
        'type_key': r['typeKey'],
        'job_id': UUID(job['id']),
        'requester_ref': requester,
    }
    f['repo'].complete_import_source(
        **args, upload_grant=job['uploadGrant'], content=content, artifact_store=store
    )
    assert (
        validate_import_job(site_id=f['site_id'], job_id=UUID(job['id']), artifact_store=store)
        == 'validated'
    )
    f['repo'].commit_import(**args)
    assert (
        process_import_commit(site_id=f['site_id'], job_id=UUID(job['id']), artifact_store=store)
        == 'completed'
    )
    current = f['repo'].get_record(**scope(f, r))
    assert current['publicContent'] == COPY and current['values'] == {'summary': 'Imported private'}
    current = f['repo'].update_record(
        **scope(f, r),
        expected_version=current['version'],
        actor_ref=requester,
        values=current['values'],
        public_content={'excerpt': 'changed', 'body': 'changed'},
    )
    restored = f['repo'].restore_record(
        **scope(f, r), version=1, expected_version=current['version'], actor_ref=requester
    )
    assert restored['publicContent'] == COPY and restored['values'] == {'summary': PRIVATE}
    assert restored['title'] == 'Imported private update'  # History context is not restored.


@pytest.mark.parametrize('changed_copy', [False, True])
def test_restore_review_effect_depends_on_semantic_copy_change(
    workspace_policy_fixture, changed_copy
):
    f = workspace_policy_fixture
    r = create_copy(f)
    r = transition(f, reviewed(f, r), 'publish')
    if changed_copy:
        r = f['repo'].update_record(
            **scope(f, r),
            expected_version=r['version'],
            actor_ref=f"user:{f['creator_id']}",
            values=r['values'],
            public_content={'excerpt': 'Changed summary', 'body': 'Changed body'},
        )
        r = transition(f, reviewed(f, r), 'publish')
    before = f['execute'](
        'SELECT semantic_revision,semantic_generation,submitter_id,fingerprint FROM sitecontent_reviewsubject WHERE record_id=%s',
        (r['id'],),
    )[0]
    previous_version = r['version']
    restored = f['repo'].restore_record(
        **scope(f, r), version=1, expected_version=r['version'], actor_ref=f"user:{f['creator_id']}"
    )
    after = f['execute'](
        'SELECT semantic_revision,semantic_generation,submitter_id,fingerprint FROM sitecontent_reviewsubject WHERE record_id=%s',
        (r['id'],),
    )[0]
    assert restored['publicContent'] == COPY and restored['version'] == previous_version + 1
    assert restored['restoration'] == {'sourceVersion': 1, 'publicContent': 'restored'}
    if changed_copy:
        assert restored['state'] == 'draft'
        assert after[0] != before[0] and after[1] > before[1] and after[2] is None
    else:
        assert restored['state'] == 'published'  # Historical draft context is never applied.
        assert after == before  # Identical bytes do not invalidate semantic approval.


def test_editor_cannot_publish_even_after_independent_approval(workspace_policy_fixture):
    f = workspace_policy_fixture
    pending = reviewed(f, create_copy(f))
    with pytest.raises(PermissionError, match='workspace_policy_forbidden'):
        f['repo'].transition_record(
            **scope(f, pending),
            expected_version=pending['version'],
            actor_ref=f"user:{f['creator_id']}",
            action='publish',
            publish_at=None,
            timezone=None,
        )
    unchanged = f['repo'].get_record(**scope(f, pending))
    assert unchanged['version'] == pending['version'] and unchanged['state'] == 'in_review'
    assert transition(f, unchanged, 'publish')['state'] == 'published'
