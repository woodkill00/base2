"""CI's disposable PostgreSQL must exercise actual restricted-role module access."""

import os
from contextlib import closing

import psycopg2
import pytest

from scripts.python.check_public_content_postgres import check as check_content
from scripts.python.check_scheduling_postgres import check as check_scheduling
from scripts.python.run_workspace_postgres_checks import repository_pool

pytestmark = [pytest.mark.integration]


def test_optional_modules_use_restricted_database_capabilities():
    assert os.environ.get('BASE2_DISPOSABLE_JOURNEY') == '1', 'disposable_database_required'
    assert os.environ.get('DB_HOST') in {
        'localhost',
        '127.0.0.1',
    }, 'local_disposable_database_required'
    user = os.environ['API_RUNTIME_DB_USER']
    password = os.environ['API_RUNTIME_DB_PASSWORD']
    assert user != os.environ['DB_USER'], 'distinct_runtime_role_required'
    with closing(
        psycopg2.connect(
            host=os.environ['DB_HOST'],
            port=os.environ.get('DB_PORT', '5432'),
            dbname=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            connect_timeout=3,
        )
    ) as owner:
        check_content(owner, repository_pool, user, password)
        check_scheduling(owner, repository_pool, user, password)
