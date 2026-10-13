"""Cold-import acceptance: run with the scheduler's 0.25 CPU/128 MiB limits."""
import json
import os
import sys
import time
from datetime import UTC, datetime
from types import SimpleNamespace

def main():
    started = time.monotonic()
    from api.services.runtime_heartbeat import _runtime_heartbeat
    from api import redis_client

    heavy_modules = ('api.db', 'api.settings', 'api.repositories.operations',
                     'api.services.operations_runtime', 'api.services.content_workspace_storage')
    assert not any(name in sys.modules for name in heavy_modules)
    os.environ['BASE2_DEPLOYMENT_EPOCH'] = 'bounded-probe-test'
    payload = json.dumps({'observedAt': datetime.now(UTC).isoformat(), 'deploymentEpoch': 'bounded-probe-test'})
    redis_client._client = SimpleNamespace(get=lambda key: payload)
    assert _runtime_heartbeat('schedules', 90) == ('healthy', 'schedules.ready', 0)
    os.environ['BASE2_DEPLOYMENT_EPOCH'] = 'different-deployment'
    assert _runtime_heartbeat('schedules', 90) == ('degraded', 'schedules.stale', 0)
    elapsed = time.monotonic() - started
    assert elapsed < 10, f'Heartbeat cold import exceeded unchanged 10-second deadline: {elapsed}'
    print(json.dumps({'status': 'pass', 'coldImportSeconds': round(elapsed, 3), 'heavyApplicationImports': False}))


if __name__ == '__main__':
    main()
