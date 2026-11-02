from __future__ import annotations

import os
import sys

import pytest


# Ensure repository root is on sys.path for imports in tests
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def pytest_sessionstart(session):
    """Validate DB schema when a DB is reachable.

    Schema ownership is Django. Tests should rely on `python manage.py migrate` having
    been run (e.g., in CI and deploy AllTests).
    """

    try:
        from api.db import db_conn

        with db_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.api_auth_users')")
            exists = cur.fetchone()[0] is not None
    except Exception:
        # No DB available: unit tests that don't require DB can still run.
        return

    if not exists:
        raise RuntimeError(
            'Database is reachable but API tables are missing. '
            'Schema ownership is Django; run `python manage.py migrate` '
            '(using project.settings.production against Postgres) before running API integration tests.'
        )


@pytest.fixture
def workspace_policy_fixture(monkeypatch):
    """Exact-owned synthetic scope, only in the disposable acceptance database.

    The runner destroys this entire disposable DB after the test phase; records
    intentionally survive each function to exercise immutable retention boundaries.
    Runtime and worker operations use their actual restricted roles, not the owner.
    """
    from uuid import UUID, uuid4
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    from api import db
    from api.repositories import settings as preferences
    from api.repositories import workspace_policy as policy
    from api.repositories.content_workspace import PostgresContentWorkspaceRepository

    if os.getenv('WORKSPACE_POLICY_DISPOSABLE') != '1':
        pytest.fail(
            'workspace policy integration requires the supported disposable PostgreSQL runner'
        )
    site = 'policy-' + uuid4().hex[:20]
    users = [uuid4() for _ in range(3)]
    org = uuid4()
    options = {
        'host': os.environ['DB_HOST'],
        'port': os.environ.get('DB_PORT', '5432'),
        'dbname': os.environ['DB_NAME'],
    }
    owner = psycopg2.connect(
        **options, user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD']
    )
    owner.autocommit = True
    runtime = ThreadedConnectionPool(
        1,
        6,
        **options,
        user=os.environ['API_RUNTIME_DB_USER'],
        password=os.environ['API_RUNTIME_DB_PASSWORD'],
    )
    monkeypatch.setattr(db, '_pool', runtime)

    def execute(sql, params=()):
        with owner.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id',%s,false)", (site,))
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else []

    for user in users:
        execute(
            'INSERT INTO api_auth_users(id,email,password_hash) VALUES(%s,%s,%s)',
            (str(user), f'{user}@example.test', 'disabled-synthetic-fixture'),
        )
    execute(
        'INSERT INTO api_identity_organizations(id,tenant_id,name) VALUES(%s,%s,%s)',
        (str(org), site, 'Synthetic workspace policy'),
    )
    for user, role in zip(users, ('editor', 'admin', 'admin'), strict=True):
        execute(
            "INSERT INTO api_identity_memberships(organization_id,user_id,role,status) VALUES(%s,%s,%s,'active')",
            (str(org), str(user), role),
        )
    policy.update_policy(
        site_id=site,
        user_id=users[1],
        expected_version=0,
        require_review=True,
        public_access='members_only',
    )
    repo = PostgresContentWorkspaceRepository()
    definition = repo.create_definition(
        site_id=site,
        actor_ref=f'user:{users[0]}',
        payload={
            'type_key': 'article',
            'name': 'Article',
            'description': '',
            'preset_id': 'custom',
            'fields': [],
        },
    )
    repo.publish_definition(
        site_id=site,
        type_key='article',
        version=definition['version'],
        expected_lock_version=definition['lockVersion'],
        confirm_lossy=False,
        actor_ref=f'user:{users[1]}',
    )

    def preference(mode):
        previous = preferences.get_notifications(user_id=users[1], tenant_id=site)
        return preferences.replace_notifications(
            user_id=users[1],
            tenant_id=site,
            expected_version=previous['version'],
            preferences=[{'event_family': 'product', 'channel': 'email', 'delivery': mode}],
        )

    preference('immediate')
    records = []

    def submit():
        record = repo.create_record(
            site_id=site,
            type_key='article',
            actor_ref=f'user:{users[0]}',
            payload={
                'title': 'Synthetic review',
                'slug': 'entry-' + uuid4().hex[:12],
                'values': {},
            },
        )
        records.append(UUID(record['id']))
        repo.transition_record(
            site_id=site,
            type_key='article',
            record_id=records[-1],
            expected_version=record['version'],
            actor_ref=f'user:{users[0]}',
            action='submit_review',
            publish_at=None,
            timezone=None,
        )
        return execute(
            'SELECT id FROM sitecontent_reviewnotificationintent WHERE site_id=%s AND record_id=%s AND recipient_id=%s',
            (site, str(records[-1]), str(users[1])),
        )[0][0]

    intent = submit()
    try:
        yield {
            'site_id': site,
            'creator_id': users[0],
            'reviewer_id': users[1],
            'second_reviewer_id': users[2],
            'record_id': records[0],
            'type_key': 'article',
            'execute': execute,
            'preference': preference,
            'submit': submit,
            'intent_id': intent,
            'repo': repo,
        }
    finally:
        owner.close()
        runtime.closeall()
