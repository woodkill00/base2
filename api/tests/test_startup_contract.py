from __future__ import annotations

import ast
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def test_required_component_failure_is_terminal_and_sanitized():
    from api.startup import StartupFailure, StartupRegistry

    registry = StartupRegistry()
    with pytest.raises(StartupFailure, match='routes initialization failed'):
        registry.initialize(
            'routes',
            required=True,
            initializer=lambda: (_ for _ in ()).throw(RuntimeError('password=secret-value')),
        )
    state = registry.snapshot()['routes']
    assert state == {'status': 'failed', 'required': True, 'reason': 'initialization_failed'}
    assert 'secret-value' not in str(state)


def test_optional_component_failure_is_explicitly_degraded():
    from api.startup import StartupRegistry

    registry = StartupRegistry()
    registry.initialize(
        'otel',
        required=False,
        initializer=lambda: (_ for _ in ()).throw(RuntimeError('token=secret-value')),
    )
    assert registry.snapshot()['otel'] == {
        'status': 'degraded',
        'required': False,
        'reason': 'initialization_failed',
    }


@pytest.mark.parametrize(
    ('db', 'schema', 'redis', 'celery', 'celery_required', 'expected'),
    [
        (True, True, True, True, False, 200),
        (False, True, True, True, False, 503),
        (True, False, True, True, False, 503),
        (True, True, False, True, False, 503),
        (True, True, True, False, False, 200),
        (True, True, True, False, True, 503),
    ],
)
def test_readiness_matrix(db, schema, redis, celery, celery_required, expected):
    from api.startup import evaluate_readiness

    status, payload = evaluate_readiness(
        probes={
            'database': lambda: db,
            'schema': lambda: schema,
            'redis': lambda: redis,
            'celery': lambda: celery,
        },
        celery_required=celery_required,
        startup_components={
            'otel': {'status': 'disabled', 'required': False, 'reason': 'not_enabled'}
        },
    )
    assert status == expected
    assert payload['ok'] is (expected == 200)
    assert payload['checks']['celery']['required'] is celery_required


def test_readiness_probe_exceptions_are_redacted():
    from api.startup import evaluate_readiness

    def failed_probe():
        raise RuntimeError('password=secret-value')

    status, payload = evaluate_readiness(
        probes={
            'database': failed_probe,
            'schema': lambda: True,
            'redis': lambda: True,
            'celery': lambda: True,
        },
        celery_required=False,
        startup_components={},
    )
    assert status == 503
    assert payload['checks']['database']['reason'] == 'probe_failed'
    assert 'secret-value' not in str(payload)


def test_api_boot_has_no_migration_authority():
    source_path = Path(__file__).parents[1] / 'main.py'
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    called_names = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert called_names.isdisjoint({'migrate', 'makemigrations', 'run_migrations'})


@pytest.mark.parametrize(
    ('tables', 'expected'), [((object(), object()), True), ((None, object()), False)]
)
def test_schema_readiness_is_read_only(monkeypatch, tables, expected):
    import api.db as db

    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = tables
    connection = MagicMock()
    connection.cursor.return_value = cursor

    @contextmanager
    def fake_db_conn():
        yield connection

    monkeypatch.setattr(db, 'db_conn', fake_db_conn)
    assert db.db_schema_ready() is expected
    cursor.execute.assert_called_once()
    assert cursor.execute.call_args.args[0].startswith('SELECT to_regclass')


def test_schema_readiness_fails_closed(monkeypatch):
    import api.db as db

    @contextmanager
    def failed_db_conn():
        raise RuntimeError('password=secret-value')
        yield

    monkeypatch.setattr(db, 'db_conn', failed_db_conn)
    assert db.db_schema_ready() is False


@pytest.mark.parametrize('endpoint', ['', 'http://collector.test/v1/traces'])
def test_enabled_telemetry_configures_selected_exporter(monkeypatch, endpoint):
    from api.otel import configure_otel

    def install_module(name, **attributes):
        module = ModuleType(name)
        for key, value in attributes.items():
            setattr(module, key, value)
        monkeypatch.setitem(sys.modules, name, module)

    trace = MagicMock()
    resource = MagicMock()
    resource.create.return_value = object()
    provider = MagicMock()
    tracer_provider = MagicMock(return_value=provider)
    batch_processor = MagicMock()
    console_exporter = MagicMock()
    simple_processor = MagicMock()
    otlp_exporter = MagicMock()
    fastapi_instrumentor = MagicMock()
    psycopg_instrumentor = MagicMock()

    install_module('opentelemetry', trace=trace)
    install_module(
        'opentelemetry.exporter.otlp.proto.http.trace_exporter',
        OTLPSpanExporter=otlp_exporter,
    )
    install_module(
        'opentelemetry.instrumentation.fastapi', FastAPIInstrumentor=fastapi_instrumentor
    )
    install_module(
        'opentelemetry.instrumentation.psycopg2', Psycopg2Instrumentor=psycopg_instrumentor
    )
    install_module('opentelemetry.sdk.resources', Resource=resource)
    install_module('opentelemetry.sdk.trace', TracerProvider=tracer_provider)
    install_module(
        'opentelemetry.sdk.trace.export',
        BatchSpanProcessor=batch_processor,
        ConsoleSpanExporter=console_exporter,
        SimpleSpanProcessor=simple_processor,
    )
    monkeypatch.setenv('OTEL_ENABLED', 'true')
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', endpoint)

    app = object()
    configure_otel(app)

    trace.set_tracer_provider.assert_called_once_with(provider)
    psycopg_instrumentor.return_value.instrument.assert_called_once_with()
    fastapi_instrumentor.instrument_app.assert_called_once_with(app)
    if endpoint:
        otlp_exporter.assert_called_once_with(endpoint=endpoint)
        batch_processor.assert_called_once_with(otlp_exporter.return_value)
        console_exporter.assert_not_called()
    else:
        console_exporter.assert_called_once_with()
        simple_processor.assert_called_once_with(console_exporter.return_value)
        otlp_exporter.assert_not_called()


def test_disabled_telemetry_is_a_noop(monkeypatch):
    from api.otel import configure_otel

    monkeypatch.delenv('OTEL_ENABLED', raising=False)
    configure_otel(object())


def test_production_rejects_e2e_support_even_with_a_key(monkeypatch):
    from api.settings import Settings

    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('JWT_SECRET', 'fixture-jwt')
    monkeypatch.setenv('TOKEN_PEPPER', 'fixture-pepper')
    monkeypatch.setenv('FRONTEND_URL', 'https://example.test')
    monkeypatch.setenv('OAUTH_STATE_SECRET', 'fixture-state')
    monkeypatch.setenv('GOOGLE_OAUTH_CLIENT_ID', 'fixture-client')
    monkeypatch.setenv('GOOGLE_OAUTH_CLIENT_SECRET', 'fixture-client-secret')
    monkeypatch.setenv('GOOGLE_OAUTH_REDIRECT_URI', 'https://example.test/callback')
    monkeypatch.setenv('E2E_TEST_MODE', 'true')
    with pytest.raises(RuntimeError, match='E2E_TEST_MODE'):
        Settings()


def test_invalid_flag_source_is_not_silently_replaced(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as main

    monkeypatch.setattr(
        main, 'get_flags', lambda: (_ for _ in ()).throw(RuntimeError('invalid flags'))
    )
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.get('/api/flags')
    assert response.status_code == 500
    assert response.json()['detail'] == 'internal_server_error'
