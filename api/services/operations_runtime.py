"""Connected, bounded runtime for Base2 operations collection and alert delivery."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import stat
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from api import redis_client
from api.db import db_ping, db_schema_ready, pool_snapshot
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
    if not 1 <= len(values) <= 256:
        raise ValueError('operations:tenant_configuration_invalid')
    import re

    if any(not re.fullmatch(r'[a-z][a-z0-9-]{2,62}', item) for item in values):
        raise ValueError('operations:tenant_configuration_invalid')
    return list(dict.fromkeys(values))


def fair_tenant_batch(
    values: list[str], *, limit: int = 16, cursor_name: str = 'collect'
) -> list[str]:
    """Select a bounded round-robin batch from the explicit tenant registry."""
    if not values or not 1 <= limit <= 16 or cursor_name not in {'collect', 'alerts'}:
        raise ValueError('operations:tenant_batch_invalid')
    client = redis_client.get_client()
    cursor = int(
        client.incrby(redis_client.key('operations', f'{cursor_name}-tenant-cursor'), limit)
    ) - limit
    start = cursor % len(values)
    count = min(limit, len(values))
    return [values[(start + offset) % len(values)] for offset in range(count)]


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


def _read_secret_file(path: str, *, maximum_bytes: int = 4096) -> str:
    target = Path(path)
    if not target.is_absolute() or target.is_symlink() or not target.is_file():
        raise ValueError('operations:secret_file_invalid')
    metadata = target.stat()
    if (
        metadata.st_size > maximum_bytes
        or metadata.st_uid not in {0, os.geteuid()}
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise ValueError('operations:secret_file_invalid')
    value = target.read_text(encoding='utf-8').strip()
    if not value:
        raise ValueError('operations:secret_file_invalid')
    return value


def _key_file(setting_name: str) -> bytes:
    encoded = _read_secret_file(str(getattr(settings, setting_name, '')))
    try:
        decoded = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
    except (ValueError, TypeError, binascii.Error) as exc:
        raise ValueError(f'operations:{setting_name.lower()}_invalid') from exc
    if len(decoded) < 32:
        raise ValueError(f'operations:{setting_name.lower()}_invalid')
    return decoded


def _receipt(name: str, timeout: int) -> tuple[str, str, int]:
    del timeout
    root = Path(os.getenv('OPERATIONS_RECEIPT_ROOT', '/var/lib/base2/operations'))
    target = root / f'{name}.json'
    try:
        payload = json.loads(target.read_text(encoding='utf-8'))
        if not isinstance(payload, dict) or set(payload) != {
            'schemaVersion',
            'kind',
            'status',
            'sourceCommit',
            'artifactDigest',
            'observedAt',
            'expiresAt',
            'digest',
        }:
            raise ValueError('receipt:shape')
        unsigned = {key: payload[key] for key in payload if key != 'digest'}
        key = _key_file('OPERATIONS_RECEIPT_INTEGRITY_KEY_FILE')
        expected = hmac.new(
            key,
            json.dumps(unsigned, sort_keys=True, separators=(',', ':')).encode(),
            hashlib.sha256,
        ).hexdigest()
        observed = datetime.fromisoformat(str(payload['observedAt']))
        expires = datetime.fromisoformat(str(payload['expiresAt']))
        current = datetime.now(timezone.utc)
        age = (current - observed).total_seconds()
        ok = (
            payload['schemaVersion'] == 1
            and payload['kind'] == name
            and payload['status'] == 'passed'
            and bool(__import__('re').fullmatch(r'[0-9a-f]{40}', str(payload['sourceCommit'])))
            and bool(__import__('re').fullmatch(r'[0-9a-f]{64}', str(payload['artifactDigest'])))
            and hmac.compare_digest(str(payload['digest']), expected)
            and 0 <= age <= settings.OPERATIONS_RECEIPT_MAX_AGE_SECONDS
            and current < expires
        )
    except (OSError, ValueError, TypeError, binascii.Error):
        ok = False
    return ('healthy' if ok else 'degraded', f'{name}.ready' if ok else f'{name}.unknown', 0)


def configured_probe_adapters() -> dict[str, Callable[[int], tuple[str, str, int]]]:
    storage_root = Path(settings.CONTENT_WORKSPACE_STORAGE_ROOT)

    def storage(timeout: int):
        return _timed(
            lambda: storage_root.is_dir(), 'objects.ready', 'objects.unavailable', timeout
        )

    def capacity(timeout: int):
        def check() -> bool:
            usage = shutil.disk_usage(storage_root if storage_root.exists() else '/')
            return usage.free / max(usage.total, 1) >= 0.10

        return _timed(check, 'capacity.ready', 'capacity.low', timeout)

    def configured(code: str):
        return lambda timeout: ('degraded', f'{code}.not-configured', min(timeout, 1))

    def database_performance(timeout: int):
        started = time.monotonic()
        available = db_ping()
        latency = min(int((time.monotonic() - started) * 1000), timeout * 1000)
        saturated = any(value['state'] == 'saturated' for value in pool_snapshot().values())
        ok = available and not saturated and latency < min(timeout * 1000, 1000)
        return (
            'healthy' if ok else 'degraded',
            'database.performance-ready' if ok else 'database.performance-degraded',
            latency,
        )

    return {
        'public.root': lambda timeout: _internal_http('/', timeout),
        'api.health': lambda timeout: _internal_http('/api/health', timeout),
        'database.ready': lambda timeout: _timed(
            db_ping, 'database.ready', 'database.unavailable', timeout
        ),
        'workers.ready': lambda timeout: _runtime_heartbeat('workers', timeout),
        'queues.delay': _queue_health,
        'objects.ready': storage,
        # These consume integrity-bound receipts from the separately bounded
        # domain/certificate controller. Absence is visible degradation, never
        # fabricated health and never a reason for this observer to gain DNS or
        # certificate mutation authority.
        'dns.canonical': lambda timeout: _receipt('dns', timeout),
        'certificate.expiry': lambda timeout: _receipt('certificate', timeout),
        'email.delivery': configured('email'),
        'schedules.freshness': lambda timeout: _runtime_heartbeat('schedules', timeout),
        'capacity.headroom': capacity,
        'monitoring.self': lambda timeout: _runtime_heartbeat('monitoring', timeout),
        'database.performance': database_performance,
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
    client = None
    lock_key = None
    lock_token = None
    if adapters is None:
        client = redis_client.get_client()
        lock_key = redis_client.tenant_key('operations-collection', tenant_id)
        lock_token = str(uuid4())
        if not client.set(lock_key, lock_token, nx=True, ex=120):
            raise RuntimeError('operations:collection_in_progress')
    try:
        catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
        results = collect_probe_results(
            catalog=catalog,
            adapters=configured_probe_adapters() if adapters is None else adapters,
            now=current,
        )
        result = operations.record_probe_batch(
            tenant_id=tenant_id, environment=environment, results=results, now=current
        )
        if adapters is None:
            mark_runtime_heartbeat('monitoring', now=current)
        return result
    finally:
        if client is not None and lock_key and lock_token:
            client.eval(
                "if redis.call('get',KEYS[1]) == ARGV[1] then "
                "return redis.call('del',KEYS[1]) else return 0 end",
                1,
                lock_key,
                lock_token,
            )


def mark_runtime_heartbeat(name: str, *, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    redis_client.get_client().set(redis_client.key('operations', name), current.isoformat(), ex=180)


def mark_queue_observation(*, published_at: datetime, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    delay_ms = max(0, int((current - published_at).total_seconds() * 1000))
    payload = json.dumps({'observedAt': current.isoformat(), 'delayMs': delay_ms})
    redis_client.get_client().set(redis_client.key('operations', 'queue-delay'), payload, ex=180)


def _runtime_heartbeat(name: str, timeout: int) -> tuple[str, str, int]:
    del timeout
    try:
        raw = redis_client.get_client().get(redis_client.key('operations', name))
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        observed = datetime.fromisoformat(str(raw))
        age = (datetime.now(timezone.utc) - observed).total_seconds()
        ok = 0 <= age <= 120
    except Exception:
        ok = False
    return (
        'healthy' if ok else 'degraded',
        f'{name}.ready' if ok else f'{name}.stale',
        0,
    )


def _queue_health(timeout: int) -> tuple[str, str, int]:
    del timeout
    try:
        client = redis_client.get_client()
        depth = int(client.llen('celery'))
        worker_ok = _runtime_heartbeat('workers', 1)[0] == 'healthy'
        if depth == 0 and worker_ok:
            return 'healthy', 'queues.empty', 0
        raw = client.get(redis_client.key('operations', 'queue-delay'))
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        value = json.loads(str(raw))
        observed = datetime.fromisoformat(str(value['observedAt']))
        delay_ms = int(value['delayMs'])
        fresh = 0 <= (datetime.now(timezone.utc) - observed).total_seconds() <= 120
        ok = worker_ok and fresh and depth <= 100 and delay_ms <= 60_000
    except Exception:
        return 'degraded', 'queues.unknown', 0
    return (
        'healthy' if ok else 'degraded',
        'queues.ready' if ok else 'queues.delayed',
        delay_ms,
    )


def discord_webhook_sender(payload: dict[str, Any]) -> str:
    url = _read_secret_file(settings.OPERATIONS_ALERT_WEBHOOK_URL_FILE)
    parsed = urlparse(url)
    if (
        parsed.scheme != 'https'
        or parsed.hostname not in {'discord.com', 'discordapp.com'}
        or not __import__('re').fullmatch(r'/api/webhooks/[0-9]+/[A-Za-z0-9._-]+', parsed.path)
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError('operations:webhook_url_invalid')
    endpoint = urlunparse(parsed._replace(query='wait=true', fragment=''))
    nonce = hashlib.sha256(str(payload['deliveryId']).encode()).hexdigest()[:25]
    body = json.dumps(
        {
            'content': (
                f"Base2 {payload['severity']} alert · {payload['summaryCode']} · "
                f"incident {payload['incidentId'][:12]}"
            ),
            'nonce': nonce,
            'enforce_nonce': True,
            'allowed_mentions': {'parse': []},
        }
    ).encode()
    request = Request(
        endpoint,
        data=body,
        method='POST',
        headers={'Content-Type': 'application/json', 'User-Agent': 'base2-operations/1'},
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310 - strict HTTPS host/path allowlist
        if not 200 <= response.status < 300:
            raise RuntimeError('operations:webhook_delivery_failed')
        result = json.loads(response.read(4096))
    message_id = str(result.get('id', ''))
    if not message_id.isdigit():
        raise RuntimeError('operations:webhook_receipt_invalid')
    return f'discord.{message_id}'


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
            claim_token=UUID(item['claimToken']),
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
        alert_key = integrity_key or _key_file('OPERATIONS_ALERT_INTEGRITY_KEY_FILE')
        delivery_key = receipt_key or _key_file('OPERATIONS_ALERT_RECEIPT_KEY_FILE')
    except ValueError:
        for item in active:
            defer(item, 'delivery.key-unavailable')
        return counters
    for item in active:
        expires_at = item['expiresAt']
        payload = sanitized_alert(
            delivery_id=item['deliveryId'],
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
        changed = operations.update_alert_delivery(
            tenant_id=tenant_id,
            delivery_id=UUID(item['deliveryId']),
            claim_token=UUID(item['claimToken']),
            status=status,
            next_attempt_at=next_attempt,
            receipt_digest=receipt_digest,
            error_code=error_code,
        )
        if not changed:
            counters['sent'] -= 1
            counters['terminal'] += 1
    return counters
