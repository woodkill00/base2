"""Fail-closed media boundary for explicitly restricted disposable previews."""
import os

from starlette.responses import JSONResponse


def restricted_preview():
    value = os.environ.get('BASE2_PREVIEW_MODE', 'full')
    if value not in {'full', 'restricted'}:
        raise ValueError('invalid_preview_mode')
    return value == 'restricted'


def require_media_enabled():
    if restricted_preview():
        raise ValueError('media_disabled_in_restricted_preview')


class RestrictedPreviewMiddleware:
    def __init__(self, app):
        self.app = app
        restricted_preview()  # Reject invalid deployment configuration at startup.

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and restricted_preview():
            path = scope.get('path', '').rstrip('/')
            if any(path == prefix or path.startswith(prefix + '/')
                   for prefix in ('/api/media', '/api/content', '/media', '/content')):
                response = JSONResponse(
                    {'detail': 'media_disabled_in_restricted_preview'}, status_code=503,
                    headers={'Cache-Control': 'no-store', 'X-Base2-Preview-Mode': 'restricted'},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
