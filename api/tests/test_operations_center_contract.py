from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from api.services.operations_center import (
    OperationsContractError,
    alert_schedule,
    collect_probe_results,
    deliver_sanitized_alert,
    canonical_dimensions,
    classify_health,
    incident_fingerprint,
    next_incident_state,
    objective_state,
    synthetic_result,
    sanitized_alert,
    validate_probe_catalog,
    verify_sanitized_alert,
)

NOW = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)


def test_health_states_are_truthful_and_stale_wins():
    assert (
        classify_health(
            enabled=False, muted=False, probe_state=None, observed_at=None, expires_at=None, now=NOW
        )
        == 'disabled'
    )
    assert (
        classify_health(
            enabled=True, muted=True, probe_state=None, observed_at=None, expires_at=None, now=NOW
        )
        == 'muted'
    )
    assert (
        classify_health(
            enabled=True, muted=False, probe_state=None, observed_at=None, expires_at=None, now=NOW
        )
        == 'unknown'
    )
    assert (
        classify_health(
            enabled=True,
            muted=False,
            probe_state='healthy',
            observed_at=NOW - timedelta(minutes=2),
            expires_at=NOW - timedelta(minutes=1),
            now=NOW,
        )
        == 'stale'
    )
    assert (
        classify_health(
            enabled=True,
            muted=False,
            probe_state='degraded',
            observed_at=NOW,
            expires_at=NOW + timedelta(minutes=1),
            now=NOW,
        )
        == 'degraded'
    )


def test_health_rejects_naive_or_impossible_time():
    with pytest.raises(OperationsContractError):
        classify_health(
            enabled=True,
            muted=False,
            probe_state='healthy',
            observed_at=NOW,
            expires_at=NOW,
            now=NOW,
        )


def test_dimensions_reject_secrets_nested_and_unbounded_values():
    assert canonical_dimensions({'region': 'test', 'attempt': 1}) == {
        'attempt': 1,
        'region': 'test',
    }
    for value in ({'password': 'x'}, {'region': {}}, {'region': 'x' * 201}):
        with pytest.raises(OperationsContractError):
            canonical_dimensions(value)


def test_synthetic_result_is_exact_source_bounded_and_deterministic():
    steps = [{'code': 'page.loaded', 'passed': True, 'durationMs': 12}]
    first = synthetic_result(
        journey='anonymous.public_page', role='anonymous', source_commit='a' * 40, steps=steps
    )
    second = synthetic_result(
        journey='anonymous.public_page', role='anonymous', source_commit='a' * 40, steps=steps
    )
    assert first == second
    assert first['status'] == 'passed'
    assert len(first['resultDigest']) == 64


def test_synthetic_result_rejects_unknown_journey_and_extra_step_data():
    with pytest.raises(OperationsContractError):
        synthetic_result(
            journey='shell.execute',
            role='administrator',
            source_commit='a' * 40,
            steps=[{'code': 'bad', 'passed': True, 'durationMs': 1}],
        )
    with pytest.raises(OperationsContractError):
        synthetic_result(
            journey='member.login',
            role='member',
            source_commit='a' * 40,
            steps=[{'code': 'login.pass', 'passed': True, 'durationMs': 1, 'body': 'secret'}],
        )


def test_incident_identity_is_tenant_bound_and_replay_stable():
    one = incident_fingerprint(
        site_id='tenant-one', service_key='api.health', code='api.unavailable'
    )
    assert one == incident_fingerprint(
        site_id='tenant-one', service_key='api.health', code='api.unavailable'
    )
    assert one != incident_fingerprint(
        site_id='tenant-two', service_key='api.health', code='api.unavailable'
    )


def test_incident_transition_handles_ack_recovery_and_recurrence():
    assert next_incident_state(prior=None, failing=True) == 'firing'
    assert next_incident_state(prior='firing', failing=True, acknowledged=True) == 'acknowledged'
    assert next_incident_state(prior='acknowledged', failing=False) == 'resolved'
    assert next_incident_state(prior='resolved', failing=True) == 'recurring'


def test_alerts_expire_stop_and_back_off_with_finite_attempts():
    assert (
        alert_schedule(severity='high', attempts=0, maximum_attempts=5, now=NOW, expires_at=NOW)[
            'status'
        ]
        == 'expired'
    )
    assert (
        alert_schedule(
            severity='high',
            attempts=5,
            maximum_attempts=5,
            now=NOW,
            expires_at=NOW + timedelta(hours=1),
        )['status']
        == 'failed'
    )
    due = alert_schedule(
        severity='critical',
        attempts=2,
        maximum_attempts=5,
        now=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    assert due == {'status': 'queued', 'nextAttemptAt': (NOW + timedelta(seconds=60)).isoformat()}


def test_objective_state_has_met_risk_and_breach_states():
    assert objective_state(successful=999, total=1000, target=0.999, warning=0.995) == 'met'
    assert objective_state(successful=996, total=1000, target=0.999, warning=0.995) == 'at_risk'
    assert objective_state(successful=900, total=1000, target=0.999, warning=0.995) == 'breached'


def test_objective_rejects_empty_or_impossible_windows():
    with pytest.raises(OperationsContractError):
        objective_state(successful=0, total=0, target=0.99, warning=0.9)


def test_probe_catalog_covers_every_required_dependency_and_is_bounded():
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads((root / 'shared/config/operations-probes-v1.json').read_text())
    assert validate_probe_catalog(catalog) == json.loads(json.dumps(catalog, sort_keys=True))
    assert len(catalog['probes']) == 16
    assert sum(item['timeoutSeconds'] for item in catalog['probes']) <= 60


def test_probe_catalog_rejects_a_batch_that_can_exceed_its_deadline():
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads((root / 'shared/config/operations-probes-v1.json').read_text())
    catalog['probes'][0]['timeoutSeconds'] = 30
    with pytest.raises(OperationsContractError, match='budget_exceeded'):
        validate_probe_catalog(catalog)


def test_collection_makes_missing_and_failed_adapters_visible():
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads((root / 'shared/config/operations-probes-v1.json').read_text())
    adapters = {
        'public.root': lambda timeout: ('healthy', 'public.ready', 4),
        'api.health': lambda timeout: (_ for _ in ()).throw(RuntimeError('offline')),
    }
    results = collect_probe_results(catalog=catalog, adapters=adapters, now=NOW)
    indexed = {item['probeId']: item for item in results}
    assert indexed['public.root']['state'] == 'healthy'
    assert indexed['api.health']['code'] == 'probe.adapter_failed'
    assert indexed['monitoring.self']['state'] == 'unknown'
    assert len(results) == 16


def test_alert_contains_only_bounded_codes_actions_and_integrity():
    payload = sanitized_alert(
        incident_id='a' * 64,
        severity='high',
        summary_code='api.unavailable',
        expires_at=NOW + timedelta(minutes=15),
    )
    assert set(payload) == {
        'schemaVersion',
        'incidentId',
        'severity',
        'summaryCode',
        'expiresAt',
        'actions',
        'digest',
    }
    assert payload['actions'] == ['acknowledge', 'open-private-evidence']
    assert len(payload['digest']) == 64


def test_alert_delivery_is_sanitized_observed_and_provider_failure_is_durable():
    payload = sanitized_alert(
        incident_id='a' * 64,
        severity='critical',
        summary_code='database.unavailable',
        expires_at=NOW + timedelta(minutes=15),
    )
    delivered = deliver_sanitized_alert(
        payload=payload,
        now=NOW,
        sender=lambda value: 'discord.message-0001'
        if value['summaryCode'] == 'database.unavailable'
        else None,
    )
    assert delivered['status'] == 'sent'
    assert len(delivered['receiptDigest']) == 64
    queued = deliver_sanitized_alert(
        payload=payload,
        now=NOW,
        sender=lambda _value: (_ for _ in ()).throw(ConnectionError('private endpoint')),
    )
    assert queued == {
        'incidentId': 'a' * 64,
        'alertDigest': payload['digest'],
        'channel': 'discord',
        'status': 'queued',
        'errorCode': 'delivery.provider_failed',
    }


def test_alert_tamper_and_expiry_fail_before_delivery():
    payload = sanitized_alert(
        incident_id='b' * 64,
        severity='high',
        summary_code='queue.stalled',
        expires_at=NOW + timedelta(minutes=1),
    )
    changed = dict(payload)
    changed['summaryCode'] = 'queue.healthy'
    with pytest.raises(OperationsContractError, match='integrity'):
        verify_sanitized_alert(changed, now=NOW)
    with pytest.raises(OperationsContractError, match='expired'):
        deliver_sanitized_alert(
            payload=payload,
            now=NOW + timedelta(minutes=2),
            sender=None,
        )
