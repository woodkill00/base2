"""Pure, bounded state contracts for the Base2 native operations center."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from queue import Empty, Queue
from threading import Thread
from typing import Any, Literal

HealthState = Literal['healthy', 'degraded', 'unavailable', 'stale', 'unknown', 'muted', 'disabled']
SEVERITIES = {'info', 'warning', 'high', 'critical'}
PROBE_KINDS = {
    'http',
    'database',
    'worker',
    'queue',
    'object-storage',
    'dns',
    'certificate',
    'email',
    'schedule',
    'capacity',
    'monitor',
    'backup',
    'restore',
    'migration',
}
JOURNEYS = {
    'anonymous.public_page',
    'member.login',
    'member.navigation',
    'editor.content_preview',
    'administrator.operations_read',
    'member.form_submit',
    'editor.media_upload',
    'member.search',
    'member.logout',
}
SECRET_KEY = re.compile(
    r'token|password|secret|credential|authorization|cookie|private.?key|body|content',
    re.I,
)
CODE = re.compile(r'^[a-z][a-z0-9_.-]{2,95}$')


class OperationsContractError(ValueError):
    pass


def validate_probe_catalog(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {'schemaVersion', 'probes', 'collection', 'retention'}
        or value.get('schemaVersion') != 1
    ):
        raise OperationsContractError('operations:probe_catalog_invalid')
    probes = value.get('probes')
    if not isinstance(probes, list) or not 1 <= len(probes) <= 32:
        raise OperationsContractError('operations:probe_catalog_invalid')
    seen = set()
    for probe in probes:
        if not isinstance(probe, dict) or set(probe) != {
            'id',
            'kind',
            'freshnessSeconds',
            'timeoutSeconds',
        }:
            raise OperationsContractError('operations:probe_invalid')
        if (
            not CODE.fullmatch(str(probe['id']))
            or probe['id'] in seen
            or probe['kind'] not in PROBE_KINDS
        ):
            raise OperationsContractError('operations:probe_invalid')
        if (
            type(probe['freshnessSeconds']) is not int
            or not 30 <= probe['freshnessSeconds'] <= 86400
        ):
            raise OperationsContractError('operations:probe_invalid')
        if type(probe['timeoutSeconds']) is not int or not 1 <= probe['timeoutSeconds'] <= 30:
            raise OperationsContractError('operations:probe_invalid')
        seen.add(probe['id'])
    if {probe['kind'] for probe in probes} != PROBE_KINDS:
        raise OperationsContractError('operations:probe_kinds_incomplete')
    if value.get('collection') != {
        'maximumProbes': 32,
        'maximumBatchSeconds': 60,
        'maximumDimensions': 16,
    }:
        raise OperationsContractError('operations:collection_policy_invalid')
    if (
        sum(probe['timeoutSeconds'] for probe in probes)
        > value['collection']['maximumBatchSeconds']
    ):
        raise OperationsContractError('operations:collection_budget_exceeded')
    if value.get('retention') != {'healthDays': 30, 'syntheticDays': 30, 'incidentDays': 365}:
        raise OperationsContractError('operations:retention_policy_invalid')
    return json.loads(json.dumps(value, sort_keys=True))


def collect_probe_results(
    *, catalog: dict[str, Any], adapters: dict[str, Any], now: datetime
) -> list[dict[str, Any]]:
    validated = validate_probe_catalog(catalog)
    results = []
    for probe in validated['probes']:
        adapter = adapters.get(probe['id'])
        if adapter is None:
            state, code, latency = 'unknown', 'probe.adapter_missing', None
        else:
            try:
                completed: Queue[Any] = Queue(maxsize=1)

                def invoke(
                    target: Any = adapter,
                    timeout: int = probe['timeoutSeconds'],
                    output: Queue[Any] = completed,
                ) -> None:
                    try:
                        output.put(('ok', target(timeout)), block=False)
                    except Exception as error:
                        output.put(('error', error), block=False)

                Thread(target=invoke, daemon=True).start()
                try:
                    outcome, response = completed.get(timeout=probe['timeoutSeconds'])
                except Empty as error:
                    raise TimeoutError('operations:adapter_timeout') from error
                if outcome == 'error':
                    raise response
                if not isinstance(response, tuple) or len(response) != 3:
                    raise OperationsContractError('operations:adapter_result_invalid')
                state, code, latency = response
                if (
                    state not in {'healthy', 'degraded', 'unavailable'}
                    or not CODE.fullmatch(str(code))
                    or type(latency) is not int
                    or not 0 <= latency <= probe['timeoutSeconds'] * 1000
                ):
                    raise OperationsContractError('operations:adapter_result_invalid')
            except Exception:
                state, code, latency = 'unavailable', 'probe.adapter_failed', None
        results.append(
            {
                'probeId': probe['id'],
                'state': state,
                'code': code,
                'latencyMs': latency,
                'observedAt': now.isoformat(),
                'expiresAt': (now + timedelta(seconds=probe['freshnessSeconds'])).isoformat(),
            }
        )
    return results


def sanitized_alert(
    *,
    delivery_id: str = '00000000-0000-0000-0000-000000000001',
    incident_id: str,
    severity: str,
    summary_code: str,
    expires_at: datetime,
    integrity_key: bytes,
) -> dict[str, Any]:
    if (
        not re.fullmatch(r'[0-9a-f-]{36}', delivery_id or '')
        or not re.fullmatch(r'[0-9a-f]{64}', incident_id or '')
        or severity not in SEVERITIES
        or not CODE.fullmatch(summary_code or '')
        or expires_at.tzinfo is None
        or not isinstance(integrity_key, bytes)
        or len(integrity_key) < 32
    ):
        raise OperationsContractError('operations:alert_invalid')
    payload = {
        'schemaVersion': 1,
        'deliveryId': delivery_id,
        'incidentId': incident_id,
        'severity': severity,
        'summaryCode': summary_code,
        'expiresAt': expires_at.isoformat(),
        'actions': ['acknowledge', 'open-private-evidence'],
    }
    payload['digest'] = hmac.new(
        integrity_key,
        json.dumps(payload, sort_keys=True, separators=(',', ':')).encode(),
        hashlib.sha256,
    ).hexdigest()
    return payload


def verify_sanitized_alert(payload: Any, *, now: datetime, integrity_key: bytes) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {
        'schemaVersion',
        'deliveryId',
        'incidentId',
        'severity',
        'summaryCode',
        'expiresAt',
        'actions',
        'digest',
    }:
        raise OperationsContractError('operations:alert_invalid')
    unsigned = {key: payload[key] for key in payload if key != 'digest'}
    if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
        raise OperationsContractError('operations:alert_key_invalid')
    expected = hmac.new(
        integrity_key,
        json.dumps(unsigned, sort_keys=True, separators=(',', ':')).encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(str(payload['digest']), expected):
        raise OperationsContractError('operations:alert_integrity_invalid')
    rebuilt = sanitized_alert(
        delivery_id=payload['deliveryId'],
        incident_id=payload['incidentId'],
        severity=payload['severity'],
        summary_code=payload['summaryCode'],
        expires_at=datetime.fromisoformat(payload['expiresAt']),
        integrity_key=integrity_key,
    )
    if rebuilt != payload:
        raise OperationsContractError('operations:alert_invalid')
    if now.tzinfo is None:
        raise OperationsContractError('operations:timezone_required')
    if now >= datetime.fromisoformat(payload['expiresAt']):
        raise OperationsContractError('operations:alert_expired')
    return json.loads(json.dumps(payload))


def deliver_sanitized_alert(
    *,
    payload: dict[str, Any],
    now: datetime,
    sender: Any,
    integrity_key: bytes,
    receipt_key: bytes,
) -> dict[str, Any]:
    if (
        not isinstance(receipt_key, bytes)
        or len(receipt_key) < 32
        or hmac.compare_digest(integrity_key, receipt_key)
    ):
        raise OperationsContractError('operations:receipt_key_invalid')
    admitted = verify_sanitized_alert(payload, now=now, integrity_key=integrity_key)
    delivery = {
        'incidentId': admitted['incidentId'],
        'alertDigest': admitted['digest'],
        'channel': 'discord',
    }
    try:
        provider_id = sender(json.loads(json.dumps(admitted)))
        if not isinstance(provider_id, str) or not CODE.fullmatch(provider_id):
            raise OperationsContractError('operations:delivery_receipt_invalid')
    except Exception:
        return {**delivery, 'status': 'queued', 'errorCode': 'delivery.provider_failed'}
    receipt = {**delivery, 'status': 'sent', 'providerReceipt': provider_id}
    receipt['receiptDigest'] = hmac.new(
        receipt_key,
        json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode(),
        hashlib.sha256,
    ).hexdigest()
    return receipt


def canonical_dimensions(value: Any) -> dict[str, str | int | float | bool]:
    if not isinstance(value, dict) or len(value) > 16:
        raise OperationsContractError('operations:dimensions_invalid')
    result: dict[str, str | int | float | bool] = {}
    for key in sorted(value):
        item = value[key]
        if (
            not isinstance(key, str)
            or not CODE.fullmatch(key)
            or SECRET_KEY.search(key)
            or not isinstance(item, str | int | float | bool)
            or isinstance(item, str)
            and len(item) > 200
        ):
            raise OperationsContractError('operations:dimensions_invalid')
        result[key] = item
    return result


def classify_health(
    *,
    enabled: bool,
    muted: bool,
    probe_state: str | None,
    observed_at: datetime | None,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> HealthState:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise OperationsContractError('operations:timezone_required')
    if not enabled:
        return 'disabled'
    if muted:
        return 'muted'
    if observed_at is None or expires_at is None or probe_state is None:
        return 'unknown'
    if observed_at.tzinfo is None or expires_at.tzinfo is None or expires_at <= observed_at:
        raise OperationsContractError('operations:sample_time_invalid')
    if current > expires_at:
        return 'stale'
    if probe_state not in {'healthy', 'degraded', 'unavailable'}:
        raise OperationsContractError('operations:probe_state_invalid')
    return probe_state  # type: ignore[return-value]


def synthetic_result(
    *, journey: str, role: str, source_commit: str, steps: list[dict[str, Any]]
) -> dict[str, Any]:
    if journey not in JOURNEYS or role not in {'anonymous', 'member', 'editor', 'administrator'}:
        raise OperationsContractError('operations:journey_invalid')
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit or ''):
        raise OperationsContractError('operations:source_invalid')
    if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
        raise OperationsContractError('operations:steps_invalid')
    normalized = []
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'code', 'passed', 'durationMs'}:
            raise OperationsContractError('operations:step_invalid')
        if (
            not CODE.fullmatch(str(step['code']))
            or type(step['passed']) is not bool
            or type(step['durationMs']) is not int
            or not 0 <= step['durationMs'] <= 30_000
        ):
            raise OperationsContractError('operations:step_invalid')
        normalized.append(
            {
                'code': step['code'],
                'passed': step['passed'],
                'durationMs': step['durationMs'],
            }
        )
    payload = {
        'journey': journey,
        'role': role,
        'sourceCommit': source_commit,
        'status': 'passed' if all(step['passed'] for step in normalized) else 'failed',
        'steps': normalized,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    payload['resultDigest'] = hashlib.sha256(canonical).hexdigest()
    return payload


def incident_fingerprint(*, site_id: str, environment: str, service_key: str, code: str) -> str:
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,62}', site_id or ''):
        raise OperationsContractError('operations:site_invalid')
    if environment not in {'preview', 'staging', 'production'}:
        raise OperationsContractError('operations:environment_invalid')
    if not CODE.fullmatch(service_key or '') or not CODE.fullmatch(code or ''):
        raise OperationsContractError('operations:incident_invalid')
    return hashlib.sha256(f'{site_id}\0{environment}\0{service_key}\0{code}'.encode()).hexdigest()


def next_incident_state(*, prior: str | None, failing: bool, acknowledged: bool = False) -> str:
    if prior not in {None, 'firing', 'acknowledged', 'resolved', 'recurring'}:
        raise OperationsContractError('operations:incident_state_invalid')
    if not failing:
        return 'resolved'
    if prior == 'resolved':
        return 'recurring'
    if acknowledged:
        return 'acknowledged'
    return prior or 'firing'


def alert_schedule(
    *,
    severity: str,
    attempts: int,
    maximum_attempts: int,
    now: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    if severity not in SEVERITIES:
        raise OperationsContractError('operations:severity_invalid')
    if (
        type(attempts) is not int
        or type(maximum_attempts) is not int
        or not 0 <= attempts <= maximum_attempts <= 10
    ):
        raise OperationsContractError('operations:attempt_invalid')
    if now.tzinfo is None or expires_at.tzinfo is None:
        raise OperationsContractError('operations:timezone_required')
    if now >= expires_at:
        return {'status': 'expired', 'nextAttemptAt': None}
    if attempts >= maximum_attempts:
        return {'status': 'failed', 'nextAttemptAt': None}
    delay = min(900, 15 * (2**attempts))
    due = min(now + timedelta(seconds=delay), expires_at)
    return {'status': 'queued', 'nextAttemptAt': due.isoformat()}


def objective_state(*, successful: int, total: int, target: float, warning: float) -> str:
    if (
        type(successful) is not int
        or type(total) is not int
        or not 0 <= successful <= total
        or total <= 0
        or not 0 <= warning <= target <= 1
    ):
        raise OperationsContractError('operations:objective_invalid')
    ratio = successful / total
    if ratio >= target:
        return 'met'
    if ratio >= warning:
        return 'at_risk'
    return 'breached'
