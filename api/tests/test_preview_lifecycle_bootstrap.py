from unittest.mock import Mock

import pytest

from api.scripts import ensure_preview_lifecycle as subject


def state(**overrides):
    return {
        'owner': subject.OWNER,
        'configuration': subject.CONFIGURATION,
        'state': 'provisioning',
        'operationId': str(subject.PROVISION_ID),
        'revision': 1,
        **overrides,
    }


def test_fresh_preview_uses_canonical_provision_and_transition(monkeypatch):
    get = Mock(
        side_effect=subject.repository.TenantLifecycleRepositoryError('tenant:lifecycle_missing')
    )
    provision = Mock(return_value=state())
    transition = Mock(return_value={'state': 'active'})
    monkeypatch.setattr(subject.repository, 'get_state', get)
    monkeypatch.setattr(subject.repository, 'provision', provision)
    monkeypatch.setattr(subject, 'persist_transition', transition)
    assert subject.ensure(enabled=True, profile=subject.PROFILE) == {
        'status': 'active',
        'created': True,
    }
    provision.assert_called_once_with(
        tenant_id=subject.PROFILE,
        owner_ref=subject.OWNER,
        operation_id=subject.PROVISION_ID,
        configuration=subject.CONFIGURATION,
    )
    transition.assert_called_once_with(
        tenant_id=subject.PROFILE,
        target='active',
        owner=subject.OWNER,
        expected_revision=1,
        operation_id=subject.ACTIVATE_ID,
    )


def test_exact_active_replay_does_not_mutate(monkeypatch):
    monkeypatch.setattr(
        subject.repository,
        'get_state',
        lambda **kw: state(state='active', operationId=str(subject.ACTIVATE_ID), revision=2),
    )
    transition = Mock()
    monkeypatch.setattr(subject, 'persist_transition', transition)
    assert subject.ensure(enabled=True, profile=subject.PROFILE)['created'] is False
    transition.assert_not_called()


@pytest.mark.parametrize(
    'overrides',
    [
        {'owner': 'another-owner'},
        {'configuration': {}},
        {'state': 'suspended'},
        {'state': 'deleted'},
        {'state': 'restoring'},
        {'revision': 3},
        {'operationId': 'other'},
        {'state': 'active'},
    ],
)
def test_existing_state_never_silently_reactivated_or_adopted(monkeypatch, overrides):
    monkeypatch.setattr(subject.repository, 'get_state', lambda **kw: state(**overrides))
    transition = Mock()
    monkeypatch.setattr(subject, 'persist_transition', transition)
    with pytest.raises(ValueError):
        subject.ensure(enabled=True, profile=subject.PROFILE)
    transition.assert_not_called()


def test_admission_precedes_database_access(monkeypatch):
    get = Mock()
    monkeypatch.setattr(subject.repository, 'get_state', get)
    assert subject.ensure(enabled=False, profile='other')['status'] == 'disabled'
    with pytest.raises(ValueError, match='profile_denied'):
        subject.ensure(enabled=True, profile='other')
    get.assert_not_called()


def test_cli_failure_is_sanitized(monkeypatch, capsys):
    monkeypatch.setattr(subject, 'ensure', Mock(side_effect=RuntimeError('private-value')))
    assert subject.main() == 1
    assert 'private-value' not in capsys.readouterr().out


def test_cli_disabled(monkeypatch, capsys):
    monkeypatch.delenv('BASE2_PREVIEW_LIFECYCLE_ENABLED', raising=False)
    assert subject.main() == 0
    assert 'disabled' in capsys.readouterr().out


def test_nonmissing_repository_errors_are_not_converted_to_provision(monkeypatch):
    monkeypatch.setattr(
        subject.repository,
        'get_state',
        Mock(
            side_effect=subject.repository.TenantLifecycleRepositoryError('tenant:integrity_error')
        ),
    )
    provision = Mock()
    monkeypatch.setattr(subject.repository, 'provision', provision)
    with pytest.raises(subject.repository.TenantLifecycleRepositoryError):
        subject.ensure(enabled=True, profile=subject.PROFILE)
    provision.assert_not_called()


def test_activation_must_return_active(monkeypatch):
    monkeypatch.setattr(subject.repository, 'get_state', lambda **kw: state())
    monkeypatch.setattr(subject, 'persist_transition', lambda **kw: {'state': 'provisioning'})
    with pytest.raises(ValueError, match='activation_failed'):
        subject.ensure(enabled=True, profile=subject.PROFILE)


def test_cli_enabled_exact_replay(monkeypatch, capsys):
    monkeypatch.setenv('BASE2_PREVIEW_LIFECYCLE_ENABLED', 'true')
    monkeypatch.setenv('SITE_PROFILE', subject.PROFILE)
    monkeypatch.setattr(
        subject.repository,
        'get_state',
        lambda **kw: state(state='active', operationId=str(subject.ACTIVATE_ID), revision=2),
    )
    assert subject.main() == 0
    assert 'active' in capsys.readouterr().out
