"""Run only on the gate-owned disposable database, never operator databases."""

from datetime import UTC, datetime, timedelta
import os
from uuid import UUID, uuid4
import pytest
from api.db import db_conn
from api.scripts.preview_media_fixture import provision
from api.repositories.identity_admin import require_permission

pytestmark = [pytest.mark.integration]


def test_real_fixture_membership_and_denial():
    assert os.environ.get('BASE2_DISPOSABLE_JOURNEY') == '1', 'disposable_database_required'
    now = datetime.now(UTC)
    run_id = now.strftime('base2-full-%Y%m%d-%H%M%S')
    config = {
        'run_id': run_id,
        'expires_at': (now + timedelta(minutes=30)).isoformat(),
        'password': 'SyntheticFixtureOnly123!',
    }
    assert provision(config, now=now)['role'] == 'editor'
    with db_conn() as connection, connection.cursor() as cursor:
        cursor.execute(
            'SELECT id FROM api_auth_users WHERE email=%s', (f'media-{run_id}@example.invalid',)
        )
        user_id = UUID(str(cursor.fetchone()[0]))
    assert (
        require_permission(user_id=user_id, tenant_id='base2-obsidian', permission='media.upload')[
            'role'
        ]
        == 'editor'
    )
    for user, tenant, permission in [
        (user_id, 'other-tenant', 'media.read'),
        (uuid4(), 'base2-obsidian', 'media.upload'),
        (user_id, 'base2-obsidian', 'member.manage'),
    ]:
        with pytest.raises(PermissionError):
            require_permission(user_id=user, tenant_id=tenant, permission=permission)
    with pytest.raises(ValueError, match='existing_organization'):
        provision(config, now=now)
    assert require_permission(user_id=user_id, tenant_id='base2-obsidian', permission='media.read')
