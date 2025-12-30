from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from ..exceptions import UpstreamTimeout, UpstreamBadResponse, ConfigError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Preserve status, ensure consistent JSON envelope
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(UpstreamTimeout)
    async def upstream_timeout_handler(request: Request, exc: UpstreamTimeout):
        return JSONResponse(status_code=504, content={"detail": "upstream_timeout"})

    @app.exception_handler(UpstreamBadResponse)
    async def upstream_bad_response_handler(request: Request, exc: UpstreamBadResponse):
        return JSONResponse(status_code=502, content={"detail": "upstream_bad_response"})

    @app.exception_handler(ConfigError)
    async def config_error_handler(request: Request, exc: ConfigError):
        return JSONResponse(status_code=500, content={"detail": "configuration_error"})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Avoid leaking internals; log via server logs; return generic error
        return JSONResponse(status_code=500, content={"detail": "internal_error"})
