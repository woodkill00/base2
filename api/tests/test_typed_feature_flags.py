from datetime import UTC, datetime, timedelta

import pytest

from api.flags import FlagError, evaluate_flag

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def definition(**overrides):
    value = {
        'schemaVersion': 1,
        'id': 'release.canary',
        'enabled': True,
        'environments': ['preview', 'staging'],
        'rolloutPercent': 100,
        'expiresAt': (NOW + timedelta(hours=1)).isoformat(),
        'revision': 1,
    }
    value.update(overrides)
    return value


def test_flag_is_exact_tenant_subject_stable_and_observable():
    first = evaluate_flag(
        definition(),
        environment='staging',
        tenant_id='tenant-one',
        subject_id='user-one',
        now=NOW,
    )
    second = evaluate_flag(
        definition(),
        environment='staging',
        tenant_id='tenant-one',
        subject_id='user-one',
        now=NOW,
    )
    assert first == second
    assert first['enabled'] is True
    assert first['reason'] == 'enabled'


def test_expiry_environment_and_rollout_fail_closed():
    cases = (
        (definition(expiresAt=NOW.isoformat()), 'staging', 'expired'),
        (definition(), 'test', 'environment-denied'),
        (definition(rolloutPercent=0), 'staging', 'rollout-denied'),
    )
    for value, environment, reason in cases:
        result = evaluate_flag(
            value,
            environment=environment,
            tenant_id='tenant-one',
            subject_id='user-one',
            now=NOW,
        )
        assert result['enabled'] is False
        assert result['reason'] == reason


def test_unknown_fields_wildcards_naive_time_and_unbounded_rollout_are_rejected():
    hostile = (
        definition(secret='not-allowed'),
        definition(environments=['*']),
        definition(rolloutPercent=101),
    )
    for value in hostile:
        with pytest.raises(FlagError):
            evaluate_flag(
                value,
                environment='staging',
                tenant_id='tenant-one',
                subject_id='user-one',
                now=NOW,
            )
    with pytest.raises(FlagError, match='context_invalid'):
        evaluate_flag(
            definition(),
            environment='staging',
            tenant_id='tenant-one',
            subject_id='user-one',
            now=datetime(2026, 9, 8),
        )
