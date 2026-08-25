import importlib
import logging
import os
import time

from celery.result import AsyncResult
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from api import tasks  # ensure tasks module is importable
from api.db import db_ping, db_schema_ready
from api.flags import get_flags
from api.logging import configure_logging
from api.metrics import metrics
from api.redis_client import ping as redis_ping
from api.settings import SITE_MANIFEST, Settings
from api.startup import StartupRegistry, evaluate_readiness

configure_logging(service='api')
boot_logger = logging.getLogger('api.boot')
try:
    settings = Settings()
except Exception as exc:
    boot_logger.error(
        'settings_import_failed',
        extra={
            'env': (os.getenv('ENV', 'development') or '').strip().lower(),
            'exception_type': type(exc).__name__,
        },
    )
    raise

_docs_enabled = bool(getattr(settings, 'API_DOCS_ENABLED', True))
_docs_url = str(getattr(settings, 'API_DOCS_URL', '/docs'))
_redoc_url = str(getattr(settings, 'API_REDOC_URL', '/redoc'))
_openapi_url = str(getattr(settings, 'API_OPENAPI_URL', '/openapi.json'))

_E2E_TEST_MODE = bool(getattr(settings, 'E2E_TEST_MODE', False))

logger = logging.getLogger('api.http')
startup_registry = StartupRegistry()


def _observe_metrics(*, status: int, latency_ms: int) -> None:
    try:
        metrics.observe(status=status, latency_ms=latency_ms)
    except Exception as exc:
        logger.warning(
            'metrics_observation_failed',
            extra={'exception_type': type(exc).__name__, 'status': status},
        )


app = FastAPI(
    title=(os.getenv('API_TITLE') or f"{SITE_MANIFEST['name']} API"),
    docs_url=(_docs_url if _docs_enabled else None),
    redoc_url=(_redoc_url if _docs_enabled else None),
    openapi_url=(_openapi_url if _docs_enabled else None),
)


@app.get('/api/site', tags=['site'])
async def site_metadata():
    """Return only public, generated site metadata."""
    return {
        'siteId': SITE_MANIFEST['siteId'],
        'name': SITE_MANIFEST['name'],
        'defaultLocale': SITE_MANIFEST['defaultLocale'],
        'navigation': SITE_MANIFEST['navigation'],
        'theme': SITE_MANIFEST['brand']['theme'],
        'manifestDigest': settings.SITE_MANIFEST_DIGEST,
    }


@app.get('/api/openapi.json', include_in_schema=False)
async def openapi_alias():
    # Keep /api/openapi.json stable for contract/runtime checks even if
    # docs/openapi are served at /openapi.json (e.g., swagger subdomain).
    return JSONResponse(app.openapi())


# Observability: optional, but enabled failures are explicitly degraded.
if os.getenv('OTEL_ENABLED', '').strip().lower() in {'1', 'true', 'yes', 'on'}:

    def _configure_otel() -> None:
        module = importlib.import_module('api.otel')
        module.configure_otel(app)

    startup_registry.initialize('otel', required=False, initializer=_configure_otel)
else:
    startup_registry.disabled('otel')


# CORS (strict allowlist; required for browser credentialed requests)
def _configure_cors() -> None:
    raw = os.getenv('CORS_ALLOW_ORIGINS', '').strip()
    origins = [o.strip() for o in raw.split(',') if o.strip()] if raw else []

    if not origins:
        # Dev-friendly defaults.
        origins = [
            'http://localhost',
            'http://localhost:3000',
            'http://127.0.0.1',
            'http://127.0.0.1:3000',
        ]
        if getattr(settings, 'FRONTEND_URL', ''):
            origins.append(str(getattr(settings, 'FRONTEND_URL', '')).rstrip('/'))

    allow_credentials = True
    if '*' in origins:
        # Disallow wildcard origins with credentials.
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'X-CSRF-Token', 'X-Requested-With'],
    )


startup_registry.initialize('cors', required=True, initializer=_configure_cors)

# Schema ownership is Django. API must not run migrations at boot.


# Middleware: request id
def _configure_request_id_middleware() -> None:
    module = importlib.import_module('api.middleware.request_id')

    @app.middleware('http')
    async def _add_request_id(request: Request, call_next):
        return await module.request_id_middleware(request, call_next)


startup_registry.initialize(
    'request_id_middleware', required=True, initializer=_configure_request_id_middleware
)


# Middleware: tenant context
def _configure_tenant_middleware() -> None:
    module = importlib.import_module('api.middleware.tenant')

    @app.middleware('http')
    async def _add_tenant_context(request: Request, call_next):
        return await module.tenant_context_middleware(request, call_next)


startup_registry.initialize(
    'tenant_middleware', required=True, initializer=_configure_tenant_middleware
)


@app.middleware('http')
async def _access_log(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = int((time.perf_counter() - start) * 1000)
        req_id = getattr(request.state, 'request_id', '')
        _observe_metrics(status=500, latency_ms=latency_ms)
        logger.exception(
            'request_failed',
            extra={
                'request_id': req_id,
                'method': request.method,
                'path': request.url.path,
                'status': 500,
                'latency_ms': latency_ms,
                'client_ip': (request.client.host if request.client else 'unknown'),
                'user_agent': request.headers.get('user-agent', ''),
            },
        )
        raise

    latency_ms = int((time.perf_counter() - start) * 1000)
    req_id = getattr(request.state, 'request_id', '')
    _observe_metrics(status=int(getattr(response, 'status_code', 0) or 0), latency_ms=latency_ms)
    logger.info(
        'request',
        extra={
            'request_id': req_id,
            'method': request.method,
            'path': request.url.path,
            'status': int(getattr(response, 'status_code', 0) or 0),
            'latency_ms': latency_ms,
            'client_ip': (request.client.host if request.client else 'unknown'),
            'user_agent': request.headers.get('user-agent', ''),
        },
    )
    return response


# Error handlers: ensure consistent {detail}
def _configure_error_handlers() -> None:
    module = importlib.import_module('api.middleware.errors')
    module.register_error_handlers(app)


startup_registry.initialize('error_handlers', required=True, initializer=_configure_error_handlers)


# Customize OpenAPI to include required security schemes from the external contract.
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    session_cookie_name = str(getattr(settings, 'SESSION_COOKIE_NAME', '') or '') or 'session'
    openapi_schema = get_openapi(
        title=app.title,
        version='0.1.0',
        description='External API contract surface',
        routes=app.routes,
    )
    comps = openapi_schema.setdefault('components', {})
    sec = comps.setdefault('securitySchemes', {})
    sec['SessionCookie'] = {
        'type': 'apiKey',
        'in': 'cookie',
        'name': session_cookie_name,
        'description': 'HttpOnly cookie carrying the primary session credential.',
    }
    sec['CsrfToken'] = {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-CSRF-Token',
        'description': 'CSRF token header required for state-changing requests.',
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _configure_openapi() -> None:
    app.openapi = custom_openapi
    app.openapi()


# External routes (proxy to Django internal)
def _include_external_routes() -> None:
    for module_name in ('auth', 'metrics', 'oauth', 'users', 'tenant', 'privacy', 'site_content'):
        module = importlib.import_module(f'api.routes.{module_name}')
        app.include_router(module.router, prefix='/api')


startup_registry.initialize('routes', required=True, initializer=_include_external_routes)

# E2E-only helpers are impossible in production by Settings validation.
if _E2E_TEST_MODE:

    def _include_test_support_routes() -> None:
        module = importlib.import_module('api.routes.test_support')
        app.include_router(module.router, prefix='/api')

    startup_registry.initialize(
        'test_support_routes',
        required=True,
        initializer=_include_test_support_routes,
    )
else:
    startup_registry.disabled('test_support_routes')

READINESS_PROBES = {
    'database': db_ping,
    'schema': db_schema_ready,
    'redis': redis_ping,
    # Celery uses the same broker availability boundary as the configured Redis broker.
    'celery': redis_ping,
}


@app.get('/api/health')
async def health():
    status, payload = evaluate_readiness(
        probes=READINESS_PROBES,
        celery_required=bool(getattr(settings, 'CELERY_REQUIRED', False)),
        startup_components=startup_registry.snapshot(),
    )
    return JSONResponse(status_code=status, content=payload)


@app.get('/api/flags')
async def flags():
    return {'flags': get_flags()}


# --- Catalog (proxy to Django internal) ---
@app.get('/api/items')
async def list_items():
    raise HTTPException(status_code=501, detail='/api/items is not implemented yet')


@app.get('/api/items/{item_id}')
async def get_item(item_id: int):
    raise HTTPException(status_code=501, detail='/api/items/{item_id} is not implemented yet')


DEFAULT_CREATE_ITEM_BODY = Body(...)


@app.post('/api/items')
async def create_item(payload: dict = DEFAULT_CREATE_ITEM_BODY):
    raise HTTPException(status_code=501, detail='/api/items POST is not implemented yet')


# --- Celery helper endpoints (optional) ---
async def _enqueue_celery_ping(request: Request):
    try:
        rid = getattr(request.state, 'request_id', None) or request.headers.get('x-request-id')
        res = tasks.ping.delay(request_id=(str(rid) if rid else None))
        return {'task_id': res.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'enqueue_failed: {e}') from e


@app.post('/api/celery/ping')
async def celery_ping_root(request: Request):
    return await _enqueue_celery_ping(request)


async def _read_celery_result(task_id: str):
    try:
        ar = AsyncResult(task_id, app=tasks.app)
        return {
            'task_id': task_id,
            'ready': ar.ready(),
            'successful': ar.successful() if ar.ready() else False,
            'state': ar.state,
            'result': (ar.result if ar.ready() else None),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'result_failed: {e}') from e


@app.get('/api/celery/result/{task_id}')
async def celery_result_root(task_id: str):
    return await _read_celery_result(task_id)


# Eager generation after every route is registered makes schema failures terminal.
startup_registry.initialize('openapi', required=True, initializer=_configure_openapi)
