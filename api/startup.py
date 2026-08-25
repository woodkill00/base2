from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any


logger = logging.getLogger('api.startup')


class StartupFailure(RuntimeError):
    """Raised when a required application component cannot initialize."""


class StartupRegistry:
    """Records redacted initialization state for required and optional components."""

    def __init__(self) -> None:
        self._components: dict[str, dict[str, Any]] = {}

    def initialize(
        self, name: str, *, required: bool, initializer: Callable[[], Any]
    ) -> Any | None:
        try:
            result = initializer()
        except Exception as exc:
            status = 'failed' if required else 'degraded'
            self._components[name] = {
                'status': status,
                'required': required,
                'reason': 'initialization_failed',
            }
            logger.error(
                'component_initialization_failed',
                extra={
                    'component': name,
                    'required': required,
                    'exception_type': type(exc).__name__,
                },
            )
            if required:
                raise StartupFailure(f'{name} initialization failed') from exc
            return None

        self._components[name] = {'status': 'ready', 'required': required}
        return result

    def disabled(self, name: str, *, required: bool = False) -> None:
        self._components[name] = {
            'status': 'disabled',
            'required': required,
            'reason': 'not_enabled',
        }

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {name: dict(state) for name, state in self._components.items()}


def evaluate_readiness(
    *,
    probes: Mapping[str, Callable[[], bool]],
    celery_required: bool,
    startup_components: Mapping[str, Mapping[str, Any]],
) -> tuple[int, dict[str, Any]]:
    required = {'database': True, 'schema': True, 'redis': True, 'celery': celery_required}
    checks: dict[str, dict[str, Any]] = {}

    for name in ('database', 'schema', 'redis', 'celery'):
        probe = probes[name]
        try:
            ok = bool(probe())
            reason = None if ok else 'unavailable'
        except Exception as exc:
            ok = False
            reason = 'probe_failed'
            logger.warning(
                'readiness_probe_failed',
                extra={'component': name, 'exception_type': type(exc).__name__},
            )
        state: dict[str, Any] = {'ok': ok, 'required': required[name]}
        if reason:
            state['reason'] = reason
        checks[name] = state

    required_startup_ready = all(
        state.get('status') == 'ready'
        for state in startup_components.values()
        if state.get('required') is True
    )
    required_probes_ready = all(
        state['ok'] for state in checks.values() if state['required'] is True
    )
    ok = required_startup_ready and required_probes_ready
    payload = {
        'ok': ok,
        'service': 'api',
        'checks': checks,
        'components': {name: dict(state) for name, state in startup_components.items()},
    }
    return (200 if ok else 503), payload
