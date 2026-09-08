"""Connected, bounded runtime for Base2 operations collection and alert delivery."""

from __future__ import annotations

import base64
import binascii
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import UUID

from api import redis_client
from api.db import db_ping, db_schema_ready
from api.repositories import operations
from api.services.operations_center import (
    alert_schedule,
    collect_probe_results,
    deliver_sanitized_alert,
    sanitized_alert,
)
from api.settings import settings

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'shared/config/operations-probes-v1.json'


def configured_tenants(raw: str | None = None) -> list[str]:
    source = raw if raw is not None else os.getenv('OPERATIONS_TENANT_IDS', settings.SITE_PROFILE)
    values = [item.strip() for item in source.split(',') if item.strip()]
    if not 1 <= len(values) <= 16:
        raise ValueError('operations:tenant_configuration_invalid')
    import re

    if any(not re.fullmatch(r'[a-z][a-z0-9-]{2,62}', item) for item in values):
        raise ValueError('operations:tenant_configuration_invalid')
    return list(dict.fromkeys(values))


def _timed(check: Callable[[], bool], healthy: str, failed: str, timeout: int):
    started = time.monotonic()
    ok = bool(check())
    latency = min(int((time.monotonic() - started) * 1000), timeout * 1000)
    return ('healthy' if ok else 'unavailable', healthy if ok else failed, latency)


def _internal_http(path: str, timeout: int) -> tuple[str, str, int]:
    base = os.getenv('OPERATIONS_INTERNAL_BASE_URL', 'http://nginx').rstrip('/')
    parsed = urlparse(base)
    if parsed.scheme != 'http' or parsed.hostname not in {'nginx', '127.0.0.1', 'localhost'}:
        return 'degraded', 'http.not-configured', 0
    started = time.monotonic()
    request = Request(f'{base}{path}', method='GET', headers={'User-Agent': 'base2-operations/1'})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - strict local allowlist above
            ok = 200 <= response.status < 400
    except Exception:
        ok = False
    latency = min(int((time.monotonic() - started) * 1000), timeout * 1000)
    return ('healthy' if ok else 'unavailable', 'http.ready' if ok else 'http.unavailable', latency)


def _receipt(name: str, timeout: int) -> tuple[str, str, int]:
    del timeout
    root = Path(os.getenv('OPERATIONS_RECEIPT_ROOT', '/var/lib/base2/operations'))
    target = root / f'{name}.json'
    try:
        age = time.time() - target.stat().st_mtime
        payload = json.loads(target.read_text(encoding='utf-8'))
        ok = payload.get('status') == 'passed' and age <= 86400
    except (OSError, ValueError, TypeError):
        ok = False
    return ('healthy' if ok else 'degraded', f'{name}.ready' if ok else f'{name}.unknown', 0)


def configured_probe_adapters() -> dict[str, Callable[[int], tuple[str, str, int]]]:
    storage_root = Path(settings.CONTENT_WORKSPACE_STORAGE_ROOT)

    def storage(timeout: int):
        return _timed(lambda: storage_root.is_dir(), 'objects.ready', 'objects.unavailable', timeout)

    def capacity(timeout: int):
        def check() -> bool:
            usage = shutil.disk_usage(storage_root if storage_root.exists() else '/')
            return usage.free / max(usage.total, 1) >= 0.10

        return _timed(check, 'capacity.ready', 'capacity.low', timeout)

    def configured(code: str):
        return lambda timeout: ('degraded', f'{code}.not-configured', min(timeout, 1))

    return {
        'public.root': lambda timeout: _internal_http('/', timeout),
        'api.health': lambda timeout: _internal_http('/api/health', timeout),
        'database.ready': lambda timeout: _timed(
            db_ping, 'database.ready', 'database.unavailable', timeout
        ),
        'workers.ready': lambda timeout: _timed(
            redis_client.ping, 'workers.broker-ready', 'workers.unavailable', timeout
        ),
        'queues.delay': lambda timeout: _timed(
            redis_client.ping, 'queues.ready', 'queues.unavailable', timeout
        ),
        'objects.ready': storage,
        'dns.canonical': configured('dns'),
        'certificate.expiry': configured('certificate'),
        'email.delivery': configured('email'),
        'schedules.freshness': lambda timeout: ('healthy', 'schedules.configured', 0),
        'capacity.headroom': capacity,
        'monitoring.self': lambda timeout: ('healthy', 'monitoring.ready', 0),
        'database.performance': lambda timeout: _timed(
            db_ping, 'database.performance-ready', 'database.performance-failed', timeout
        ),
        'backup.freshness': lambda timeout: _receipt('backup', timeout),
        'restore.last-drill': lambda timeout: _receipt('restore', timeout),
        'migrations.state': lambda timeout: _timed(
            db_schema_ready, 'migrations.ready', 'migrations.unknown', timeout
        ),
    }


def collect_site(
    *,
    tenant_id: str,
    environment: str,
    now: datetime | None = None,
    adapters: dict[str, Any] | None = None,
) -> dict[str, int]:
    current = now or datetime.now(timezone.utc)
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    results = collect_probe_results(
        catalog=catalog,
        adapters=configured_probe_adapters() if adapters is None else adapters,
        now=current,
    )
    return operations.record_probe_batch(
        tenant_id=tenant_id, environment=environment, results=results, now=current
    )


def _key(name: str) -> bytes:
    encoded = os.getenv(name, '').strip()
    try:
        decoded = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
    except (ValueError, TypeError, binascii.Error) as exc:
        raise ValueError(f'operations:{name.lower()}_invalid') from exc
    if len(decoded) < 32:
        raise ValueError(f'operations:{name.lower()}_invalid')
    return decoded


def dispatch_alerts(
    *,
    tenant_id: str,
    sender: Callable[[dict[str, Any]], str],
    now: datetime | None = None,
    limit: int = 25,
    integrity_key: bytes | None = None,
    receipt_key: bytes | None = None,
) -> dict[str, int]:
    current = now or datetime.now(timezone.utc)
    queued = operations.due_alert_deliveries(tenant_id=tenant_id, now=current, limit=limit)
    if not queued:
        return {'due': 0, 'sent': 0, 'deferred': 0, 'terminal': 0}
    counters = {'due': len(queued), 'sent': 0, 'deferred': 0, 'terminal': 0}

    def defer(item: dict[str, Any], error_code: str) -> None:
        schedule = alert_schedule(
            severity=item['severity'],
            attempts=item['attempts'] + 1,
            maximum_attempts=item['maximumAttempts'],
            now=current,
            expires_at=item['expiresAt'],
        )
        status = schedule['status']
        next_attempt = (
            datetime.fromisoformat(schedule['nextAttemptAt']) if schedule['nextAttemptAt'] else None
        )
        operations.update_alert_delivery(
            tenant_id=tenant_id,
            delivery_id=UUID(item['deliveryId']),
            expected_attempts=item['attempts'],
            status=status,
            next_attempt_at=next_attempt,
            error_code=error_code,
        )
        counters['deferred' if status == 'queued' else 'terminal'] += 1

    active = []
    for item in queued:
        if current >= item['expiresAt']:
            defer(item, 'delivery.expired')
        else:
            active.append(item)
    if not active:
        return counters
    try:
        alert_key = integrity_key or _key('OPERATIONS_ALERT_INTEGRITY_KEY')
        delivery_key = receipt_key or _key('OPERATIONS_ALERT_RECEIPT_KEY')
    except ValueError:
        for item in active:
            defer(item, 'delivery.key-unavailable')
        return counters
    for item in active:
        expires_at = item['expiresAt']
        payload = sanitized_alert(
            incident_id=item['incidentFingerprint'],
            severity=item['severity'],
            summary_code=item['summaryCode'],
            expires_at=expires_at,
            integrity_key=alert_key,
        )
        result = deliver_sanitized_alert(
            payload=payload,
            now=current,
            sender=sender,
            integrity_key=alert_key,
            receipt_key=delivery_key,
        )
        if result['status'] == 'sent':
            status = 'sent'
            next_attempt = None
            receipt_digest = result['receiptDigest']
            error_code = ''
            counters['sent'] += 1
        else:
            defer(item, result['errorCode'])
            continue
        operations.update_alert_delivery(
            tenant_id=tenant_id,
            delivery_id=UUID(item['deliveryId']),
            expected_attempts=item['attempts'],
            status=status,
            next_attempt_at=next_attempt,
            receipt_digest=receipt_digest,
            error_code=error_code,
        )
    return counters
