"""Local fixture-contract checks; these are not PostgreSQL authorization proofs."""

from uuid import UUID

import pytest

from api.tests import test_content_public_authoring_postgres as journey
from api.settings import settings


@pytest.mark.parametrize(
    'action, expected_actor',
    [('submit_review', 'creator_id'), ('schedule', 'creator_id'), ('publish', 'reviewer_id')],
)
def test_journey_selects_existing_actor_for_required_transition_permission(action, expected_actor):
    calls = []

    class Repo:
        def transition_record(self, **kwargs):
            calls.append(kwargs)
            return {'version': 3}

    f = {'repo': Repo(), 'site_id': 'site-a', 'creator_id': UUID(int=1), 'reviewer_id': UUID(int=2)}
    record = {'id': str(UUID(int=3)), 'typeKey': 'article', 'version': 2}
    assert journey.transition(f, record, action) == {'version': 3}
    assert calls[0]['actor_ref'] == f'user:{f[expected_actor]}'
    assert calls[0]['expected_version'] == 2 and calls[0]['site_id'] == 'site-a'


def test_import_journey_configures_only_synthetic_cursor_key_before_import(monkeypatch, tmp_path):
    from api.services import content_workspace_storage

    class ReachedImport(Exception):
        pass

    class Repo:
        def create_import(self, **kwargs):
            assert len(settings.TOKEN_PEPPER.encode()) >= 16
            assert settings.TOKEN_PEPPER.startswith('synthetic-')
            raise ReachedImport

    monkeypatch.setattr(settings, 'TOKEN_PEPPER', '')
    monkeypatch.setattr(
        journey, 'create_copy', lambda f: {'slug': 'public-copy', 'typeKey': 'article'}
    )
    monkeypatch.setattr(
        content_workspace_storage, 'PrivateArtifactStore', lambda *args, **kwargs: object()
    )
    f = {'repo': Repo(), 'site_id': 'site-a', 'creator_id': UUID(int=1)}
    with pytest.raises(ReachedImport):
        journey.test_import_update_history_restores_public_copy_without_import_authoring(
            f, tmp_path, monkeypatch
        )


def test_viewer_denial_journey_expects_production_permission_exception(monkeypatch):
    class Repo:
        writes = 0

        def update_record(self, **kwargs):
            self.writes += 1
            if self.writes == 3:
                raise PermissionError('workspace_policy_forbidden')
            return {
                'id': str(UUID(int=3)),
                'typeKey': 'article',
                'version': self.writes + 1,
                'values': {},
                'publicContent': kwargs.get('public_content', journey.COPY),
            }

        def list_versions(self, **kwargs):
            return {'items': []}

        def get_record(self, **kwargs):
            if kwargs['site_id'] == 'other-site':
                raise ValueError('content_not_found')
            return {'publicContent': {'excerpt': '', 'body': ''}}

    repo = Repo()
    roles = []
    f = {
        'repo': repo,
        'site_id': 'site-a',
        'creator_id': UUID(int=1),
        'execute': lambda *args: roles.append(args),
    }
    monkeypatch.setattr(
        journey,
        'create_copy',
        lambda f: {'id': str(UUID(int=3)), 'typeKey': 'article', 'version': 1, 'values': {}},
    )
    journey.test_clear_omission_stale_role_and_tenant_denials(f)
    assert repo.writes == 3 and len(roles) == 1
