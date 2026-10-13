"""Redis-only heartbeat reader for resource-constrained container health probes.

Do not import database, application settings, storage or operations orchestration
here: importing those modules can exceed the production probe's time budget.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from api import redis_client


def _runtime_heartbeat(name: str, timeout: int) -> tuple[str, str, int]:
    try:
        raw = redis_client.get_client().get(redis_client.key('operations', name))
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        value = json.loads(str(raw))
        observed = datetime.fromisoformat(str(value['observedAt']))
        age = (datetime.now(timezone.utc) - observed).total_seconds()
        max_age = max(30, min(int(timeout), 120))
        expected_epoch = os.environ.get('BASE2_DEPLOYMENT_EPOCH', 'development')
        ok = 0 <= age <= max_age and value.get('deploymentEpoch') == expected_epoch
    except Exception:
        ok = False
    return (
        'healthy' if ok else 'degraded',
        f'{name}.ready' if ok else f'{name}.stale',
        0,
    )
