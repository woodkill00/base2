from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from ..exceptions import UpstreamTimeout, UpstreamBadResponse, ConfigError


def _workspace_error(request: Request, code: str, *, field_issues=None):
    correlation_id = str(getattr(request.state, 'request_id', '') or '')
    return {
        'detail': code,
        'error': {
            'code': code,
            'message': 'The content workspace request could not be completed.',
            'field_issues': field_issues or [],
            'retryable': code == 'content_dependency_unavailable',
            'correlation_id': correlation_id,
        },
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Preserve status, ensure consistent JSON envelope
        if request.url.path.startswith('/api/content/v1'):
            detail = exc.detail if isinstance(exc.detail, str) else 'content_schema_invalid'
            return JSONResponse(
                status_code=exc.status_code,
                content=_workspace_error(request, detail),
                headers=getattr(exc, 'headers', None),
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={'detail': exc.detail},
            headers=getattr(exc, 'headers', None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        if request.url.path.startswith('/api/content/v1'):
            issues = [
                {'location': list(item.get('loc', ())), 'code': str(item.get('type', 'invalid'))}
                for item in exc.errors()[:32]
            ]
            return JSONResponse(
                status_code=422,
                content=_workspace_error(request, 'content_schema_invalid', field_issues=issues),
            )
        return JSONResponse(status_code=422, content={'detail': exc.errors()})

    @app.exception_handler(UpstreamTimeout)
    async def upstream_timeout_handler(request: Request, exc: UpstreamTimeout):
        return JSONResponse(status_code=504, content={'detail': 'upstream_timeout'})

    @app.exception_handler(UpstreamBadResponse)
    async def upstream_bad_response_handler(request: Request, exc: UpstreamBadResponse):
        return JSONResponse(status_code=502, content={'detail': 'upstream_bad_response'})

    @app.exception_handler(ConfigError)
    async def config_error_handler(request: Request, exc: ConfigError):
        return JSONResponse(status_code=500, content={'detail': 'configuration_error'})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Avoid leaking internals; log via server logs; return generic error
        return JSONResponse(status_code=500, content={'detail': 'internal_server_error'})
