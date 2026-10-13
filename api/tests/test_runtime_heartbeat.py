"""Lightweight health probes must not import the application or accept stale proof."""
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from api.services import runtime_heartbeat as probe


@pytest.mark.parametrize('age,epoch,timeout,healthy', [(0, 'current', 1, True), (29, 'current', 1, True),
    (31, 'current', 1, False), (-10, 'current', 1, False), (0, 'old', 1, False),
    (89, 'current', 90, True), (91, 'current', 90, False),
    (119, 'current', 999, True), (121, 'current', 999, False)])
def test_heartbeat_preserves_freshness_and_epoch(monkeypatch, age, epoch, timeout, healthy):
    client = MagicMock()
    client.get.return_value = json.dumps({'observedAt': (datetime.now(UTC)-timedelta(seconds=age)).isoformat(), 'deploymentEpoch': epoch}).encode()
    monkeypatch.setattr(probe.redis_client, 'get_client', lambda: client)
    monkeypatch.setenv('BASE2_DEPLOYMENT_EPOCH', 'current')
    assert (probe._runtime_heartbeat('schedules', timeout)[0] == 'healthy') is healthy
    client.get.assert_called_once_with(probe.redis_client.key('operations', 'schedules'))


@pytest.mark.parametrize('raw', [None, b'bad-json', b'{}', b'[]', b'{"observedAt":"invalid"}'])
def test_malformed_or_missing_evidence_is_degraded(monkeypatch, raw):
    client = MagicMock()
    client.get.return_value = raw
    monkeypatch.setattr(probe.redis_client, 'get_client', lambda: client)
    assert probe._runtime_heartbeat('schedules', 90) == ('degraded', 'schedules.stale', 0)


def test_unavailable_redis_is_degraded(monkeypatch):
    client = MagicMock()
    client.get.side_effect = ConnectionError('unavailable')
    monkeypatch.setattr(probe.redis_client, 'get_client', lambda: client)
    assert probe._runtime_heartbeat('schedules', 90)[0] == 'degraded'


def test_probe_import_excludes_heavy_application_and_every_compose_consumer_uses_it():
    command = ('import sys; from api.services.runtime_heartbeat import _runtime_heartbeat; '
               'assert not any(m in sys.modules for m in '
               '("api.db", "api.settings", "api.repositories.operations", '
               '"api.services.operations_runtime", "api.services.content_workspace_storage"))')
    subprocess.run([sys.executable, '-c', command], check=True, timeout=10)
    root = Path(__file__).resolve().parents[2]
    for name, count in [('development.docker.yml', 5), ('local.docker.yml', 4)]:
        text = (root/name).read_text()
        assert text.count('from api.services.runtime_heartbeat import _runtime_heartbeat') == count
        assert 'from api.services.operations_runtime import _runtime_heartbeat' not in text
    workflow = (root/'.github/workflows/ci-smoke.yml').read_text()
    assert 'runtime_heartbeat_container_acceptance.py' in workflow
    assert '--cpus .25 --memory 128m' in workflow
