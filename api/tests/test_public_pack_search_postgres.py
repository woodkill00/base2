"""Actual restricted-worker projection correction; disposable PostgreSQL required.

Sources are created, independently reviewed and published through the normal
repository. Only projection fixtures emulate previously indexed legacy URLs.
No publication bypass, schema change or owner write seeds supported content.
"""

from contextlib import contextmanager
from uuid import UUID

import pytest

from api.db import db_conn, workspace_worker_db_conn
from api.repositories import workspace_policy as policy
from api.services import content_workspace_worker as worker

pytestmark = pytest.mark.integration


@pytest.fixture(
    params=[('blog-post', '/blog'), ('doc-page', '/docs'), ('portfolio-item', '/portfolio')]
)
def pack_record(workspace_policy_fixture, request):
    f = workspace_policy_fixture
    key, path = request.param
    repo, site = f['repo'], f['site_id']
    creator, reviewer = f"user:{f['creator_id']}", f"user:{f['reviewer_id']}"
    definition = repo.create_definition(
        site_id=site,
        actor_ref=creator,
        payload={
            'type_key': key,
            'name': 'Synthetic pack',
            'description': '',
            'preset_id': 'custom',
            'fields': [],
        },
    )
    repo.publish_definition(
        site_id=site,
        type_key=key,
        version=definition['version'],
        expected_lock_version=definition['lockVersion'],
        confirm_lossy=False,
        actor_ref=reviewer,
    )
    record = repo.create_record(
        site_id=site,
        type_key=key,
        actor_ref=creator,
        payload={'title': 'Synthetic pack entry', 'slug': 'entry', 'values': {}},
    )
    record_id = UUID(record['id'])
    submitted = repo.transition_record(
        site_id=site,
        type_key=key,
        record_id=record_id,
        expected_version=record['version'],
        actor_ref=creator,
        action='submit_review',
        publish_at=None,
        timezone=None,
    )
    policy.review_action(
        site_id=site,
        type_key=key,
        record_id=record_id,
        user_id=f['reviewer_id'],
        expected_version=submitted['version'],
    )
    published = repo.transition_record(
        site_id=site,
        type_key=key,
        record_id=record_id,
        expected_version=submitted['version'],
        actor_ref=reviewer,
        action='publish',
        publish_at=None,
        timezone=None,
    )
    return {
        **f,
        'record_id': record_id,
        'type_key': key,
        'path': path + '/entry',
        'version': published['version'],
    }


def index(f, **overrides):
    return worker.index_workspace_record(
        **{
            'site_id': f['site_id'],
            'record_id': f['record_id'],
            'job_version': f['version'],
            **overrides,
        }
    )


def document(f):
    with workspace_worker_db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        cur.execute(
            'SELECT row_to_json(d) FROM sitecontent_searchdocument d '
            'WHERE content_id=%s AND site_id=%s',
            (str(f['record_id']), f['site_id']),
        )
        return cur.fetchone()[0]


def projection_fixture(f, assignment, params):
    # Fixed assignments only, in this fixture's exact scope and actual worker role.
    with workspace_worker_db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        cur.execute(
            'UPDATE sitecontent_searchdocument SET '
            + assignment
            + ' WHERE content_id=%s AND site_id=%s',
            (*params, str(f['record_id']), f['site_id']),
        )
        assert cur.rowcount == 1
        conn.commit()


def discovered(f, monkeypatch):
    """Real worker SQL predicates, scoped to one fixture before ORDER/LIMIT.

    Worker SELECT intentionally permits global discovery even when tenant-bound.
    This adapter only ANDs a fixed tenant filter around the *unchanged* production
    OR expression. It proves PostgreSQL predicate behavior, not global fairness
    or execution of the exact unmodified discovery statement. No rows are faked.
    """

    class ScopedCursor:
        def __init__(self, cursor):
            self.cursor = cursor

        def __enter__(self):
            self.cursor.__enter__()
            return self

        def __exit__(self, *args):
            return self.cursor.__exit__(*args)

        def execute(self, sql, params):
            prefix, where, remainder = sql.partition('WHERE ')
            predicate, order, suffix = remainder.partition('ORDER BY ')
            assert where and order and 'WHERE ' not in remainder
            assert ' '.join(prefix.split()) == (
                'SELECT c.site_id, c.id, c.version FROM sitecontent_contentrecord c '
                'LEFT JOIN sitecontent_searchdocument d '
                'ON d.content_id=c.id AND d.site_id=c.site_id'
            )
            assert ' '.join(suffix.split()) == 'c.updated_at, c.id LIMIT %s'
            assert params == (list(worker.PUBLIC_PACK_PATHS), 25)
            assert predicate.count('%s') == 1
            # Keep the whole existing predicate and its parameter intact; only
            # add a tenant conjunction outside it, ahead of original ORDER/LIMIT.
            scoped = prefix + 'WHERE c.site_id=%s AND (' + predicate + ') ' + order + suffix
            assert scoped == (
                prefix + 'WHERE c.site_id=%s AND (' + predicate + ') ORDER BY ' + suffix
            )
            self.cursor.execute(scoped, (f['site_id'], *params))

        def fetchall(self):
            return self.cursor.fetchall()

    class ScopedConnection:
        def __init__(self, connection):
            self.connection = connection

        def cursor(self):
            return ScopedCursor(self.connection.cursor())

    @contextmanager
    def scoped_connection():
        with workspace_worker_db_conn(tenant_id=f['site_id']) as conn:
            yield ScopedConnection(conn)

    with monkeypatch.context() as patch:
        patch.setattr(worker, 'db_conn', scoped_connection)
        rows = worker.due_index_records()
    assert all(site == f['site_id'] for site, _, _ in rows)
    return rows


def source_history(f):
    return [
        f['execute'](sql, (str(f['record_id']),))
        for sql in (
            'SELECT row_to_json(c) FROM sitecontent_contentrecord c WHERE id=%s',
            'SELECT row_to_json(r) FROM sitecontent_contentrevision r WHERE content_id=%s ORDER BY id',
            'SELECT row_to_json(a) FROM sitecontent_reviewapproval a WHERE record_id=%s ORDER BY id',
        )
    ]


def test_new_and_equal_time_legacy_projection_preserves_identity_history_and_privacy(
    pack_record, monkeypatch
):
    f = pack_record
    with workspace_worker_db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        cur.execute(
            'SELECT rolsuper, rolbypassrls, current_user = pg_get_userbyid('
            "(SELECT relowner FROM pg_class WHERE oid='sitecontent_searchdocument'::regclass)) "
            'FROM pg_roles WHERE rolname=current_user'
        )
        assert cur.fetchone() == (False, False, False)
    assert index(f) == 'indexed'
    assert document(f)['url_path'] == f['path']
    projection_fixture(f, 'url_path=%s', (f"/{f['type_key']}/entry",))
    before, history = document(f), source_history(f)
    candidate = (f['site_id'], str(f['record_id']), f['version'])
    assert candidate in discovered(f, monkeypatch)
    assert index(f, site_id='unrelated-site') == 'not_found'
    assert document(f) == before
    assert index(f) == 'indexed'
    assert document(f) == {**before, 'url_path': f['path']}
    assert source_history(f) == history
    assert candidate not in discovered(f, monkeypatch)
    assert index(f) == 'current'
    assert document(f) == {**before, 'url_path': f['path']}

    assert candidate not in discovered(f, monkeypatch)

    # Public SQL must still obey live tenant/workspace policy, not cached visibility.
    def publicly_visible(site):
        with db_conn(tenant_id=site) as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM sitecontent_searchdocument WHERE content_id=%s',
                (str(f['record_id']),),
            )
            return cur.fetchall()

    assert publicly_visible(f['site_id']) == []
    policy.update_policy(
        site_id=f['site_id'],
        user_id=f['reviewer_id'],
        expected_version=1,
        require_review=True,
        public_access='public_allowed',
    )
    assert len(publicly_visible(f['site_id'])) == 1
    assert publicly_visible('unrelated-site') == []
    policy.update_policy(
        site_id=f['site_id'],
        user_id=f['reviewer_id'],
        expected_version=2,
        require_review=True,
        public_access='members_only',
    )
    assert publicly_visible(f['site_id']) == []


@pytest.mark.parametrize('case', ['custom', 'newer', 'stale_job', 'tombstone', 'private'])
def test_projection_correction_boundaries(pack_record, case, monkeypatch):
    f = pack_record
    assert index(f) == 'indexed'
    projection_fixture(f, 'url_path=%s', (f"/{f['type_key']}/entry",))
    if case == 'custom':
        projection_fixture(f, 'url_path=%s', ('/operator/custom-entry',))
    elif case == 'newer':
        projection_fixture(f, "source_updated_at=source_updated_at + INTERVAL '1 second'", ())
    elif case == 'tombstone':
        projection_fixture(f, 'tombstoned_at=NOW()', ())
    elif case == 'private':
        projection_fixture(f, "visibility='private', title='Retained projection title'", ())
    before, history = document(f), source_history(f)
    candidate = (f['site_id'], str(f['record_id']), f['version'])
    assert (candidate in discovered(f, monkeypatch)) == (case in {'stale_job', 'private'})
    if case == 'stale_job':
        assert index(f, job_version=f['version'] - 1) == 'stale_job'
    else:
        assert index(f) == ('indexed' if case == 'private' else 'current')
    assert document(f) == ({**before, 'url_path': f['path']} if case == 'private' else before)
    assert source_history(f) == history
