"""Runtime workers observe API schema health without catalog authority."""
import json
from unittest.mock import MagicMock

import pytest

from api.services import operations_runtime as runtime


def response(body, status=200):
    result = MagicMock(status=status)
    result.__enter__.return_value = result
    result.read.return_value = body
    return result


def observe(monkeypatch, body, status=200):
    result = response(body, status)
    opener = MagicMock()
    opener.open.return_value = result
    monkeypatch.setattr(runtime, 'build_opener', lambda *args: opener, raising=False)
    monkeypatch.setenv('OPERATIONS_INTERNAL_BASE_URL', 'http://nginx')
    # A worker must never retry via its denied schema-ledger connection.
    monkeypatch.setattr(runtime, 'db_schema_ready', lambda: pytest.fail('direct schema read'), raising=False)
    outcome = runtime.configured_probe_adapters('site-a')['migrations.state'](4)
    return outcome, opener, result


@pytest.mark.parametrize('payload,status,healthy', [
    ({'ok': True, 'service': 'api', 'checks': {'schema': {'ok': True, 'required': True}}}, 200, True),
    ({'ok': True, 'service': 'api', 'checks': {'schema': {'ok': False, 'required': True}}}, 200, False),
    ({'ok': False, 'service': 'api', 'checks': {'schema': {'ok': True, 'required': True}}}, 503, False),
    ({'ok': False, 'service': 'api', 'checks': {'schema': {'ok': True, 'required': True}}}, 200, False),
    ({'ok': True, 'service': 'api', 'checks': {'schema': {'ok': 'true', 'required': True}}}, 200, False),
    ({'ok': True, 'service': 'api', 'checks': {'schema': {'ok': 1, 'required': True}}}, 200, False),
    ({'ok': True, 'service': 'api', 'checks': {'schema': {'ok': True, 'required': False}}}, 200, False),
    ({'ok': True, 'service': 'other', 'checks': {'schema': {'ok': True, 'required': True}}}, 200, False),
    ({'ok': True, 'service': 'api'}, 200, False),
    ({'ok': True, 'service': 'api', 'checks': []}, 200, False),
    ({'ok': True, 'service': 'api', 'checks': {'schema': []}}, 200, False),
    ([], 200, False),
    ({}, 204, False),
])
def test_migration_probe_requires_exact_readiness_contract(monkeypatch, payload, status, healthy):
    outcome, opener, result = observe(monkeypatch, json.dumps(payload).encode(), status)
    assert outcome[:2] == (('healthy', 'migrations.ready') if healthy else ('unavailable', 'migrations.unknown'))
    request = opener.open.call_args.args[0]
    assert request.full_url == 'http://nginx/api/health'
    assert opener.open.call_args.kwargs == {'timeout': 4}
    if status == 200:
        result.read.assert_called_once_with(4097)


@pytest.mark.parametrize('body', [b'{', b'\xff', b' ' * 4097])
def test_invalid_or_oversized_migration_response_is_unknown(monkeypatch, body):
    outcome, _, _ = observe(monkeypatch, body)
    assert outcome[:2] == ('unavailable', 'migrations.unknown')


@pytest.mark.parametrize('url', [
    'https://nginx', 'http://remote.example', 'http://user:secret@nginx',
    'http://@nginx', 'http://:@nginx',
    'http://nginx/', 'http://nginx/path', 'http://nginx?redirect=remote', 'http://nginx#fragment',
    'http://nginx:0', 'http://nginx:65536', 'http://nginx:not-a-port', 'http://[invalid',
])
def test_migration_probe_rejects_noncanonical_destination_without_network(monkeypatch, url):
    monkeypatch.setenv('OPERATIONS_INTERNAL_BASE_URL', url)
    opener = MagicMock(side_effect=AssertionError('must not open'))
    monkeypatch.setattr(runtime, 'build_opener', opener)
    assert runtime.configured_probe_adapters('site-a')['migrations.state'](4) == (
        'unavailable', 'migrations.unknown', 0,
    )
    opener.assert_not_called()


@pytest.mark.parametrize('failure', [TimeoutError('timeout'), OSError('offline')])
def test_migration_transport_failure_remains_unknown_without_sql(monkeypatch, failure):
    opener = MagicMock()
    opener.open.side_effect = failure
    monkeypatch.setattr(runtime, 'build_opener', lambda *args: opener)
    monkeypatch.setenv('OPERATIONS_INTERNAL_BASE_URL', 'http://nginx:8080')
    monkeypatch.setattr(runtime, 'db_schema_ready', lambda: pytest.fail('direct schema read'), raising=False)
    assert runtime.configured_probe_adapters('site-a')['migrations.state'](4)[:2] == (
        'unavailable', 'migrations.unknown',
    )
    assert opener.open.call_args.args[0].full_url == 'http://nginx:8080/api/health'


@pytest.mark.parametrize('code', [301, 302, 303, 307, 308])
def test_migration_redirect_is_rejected_before_any_followup_request(monkeypatch, code):
    from urllib.error import HTTPError

    captured = []
    opener = MagicMock()
    opener.open.side_effect = HTTPError('http://nginx/api/health', code, 'redirect', {}, None)

    def build(*handlers):
        captured.extend(handlers)
        return opener

    monkeypatch.setattr(runtime, 'build_opener', build)
    monkeypatch.setenv('OPERATIONS_INTERNAL_BASE_URL', 'http://nginx')
    assert runtime.configured_probe_adapters('site-a')['migrations.state'](4)[:2] == (
        'unavailable', 'migrations.unknown',
    )
    from urllib.request import ProxyHandler

    proxies = [handler for handler in captured if isinstance(handler, ProxyHandler)]
    assert len(proxies) == 1 and proxies[0].proxies == {}
    redirect = next(handler for handler in captured if isinstance(handler, runtime._NoSchemaRedirect))
    assert redirect.redirect_request(None, None, code, 'redirect', {}, 'http://remote.example') is None
    opener.open.assert_called_once()


@pytest.mark.parametrize('timeout', [0, 6, True])
def test_migration_timeout_cannot_exceed_bounded_catalog_limit(monkeypatch, timeout):
    monkeypatch.setenv('OPERATIONS_INTERNAL_BASE_URL', 'http://nginx')
    opener = MagicMock()
    monkeypatch.setattr(runtime, 'build_opener', opener)
    assert runtime.configured_probe_adapters('site-a')['migrations.state'](timeout) == (
        'unavailable', 'migrations.unknown', 0,
    )
    opener.assert_not_called()


def test_invalid_request_construction_remains_unknown(monkeypatch):
    monkeypatch.setenv('OPERATIONS_INTERNAL_BASE_URL', 'http://nginx')
    monkeypatch.setattr(runtime, 'Request', MagicMock(side_effect=ValueError('invalid URL')))
    assert runtime.configured_probe_adapters('site-a')['migrations.state'](4)[:2] == (
        'unavailable', 'migrations.unknown',
    )
