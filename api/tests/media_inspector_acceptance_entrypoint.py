"""Test-only supervisor entrypoint with an explicit signed-definition reference clock."""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from api.services import media_inspector_service as service


def main() -> int:
    arguments = sys.argv[1:]
    healthcheck = arguments[-1:] == ["--healthcheck"]
    if healthcheck:
        arguments = arguments[:-1]
    if len(arguments) != 2 or arguments[0] != "--reference-epoch":
        return 64
    try:
        epoch = int(arguments[1])
        reference_now = datetime.fromtimestamp(epoch, tz=UTC)
    except (OverflowError, ValueError):
        return 64
    if str(epoch) != arguments[1] or epoch <= 0:
        return 64

    original_health = service._scanner_health
    original_inspect = service.inspect_request

    def referenced_health():
        return original_health(now=lambda: reference_now)

    def referenced_inspect(request, content, **keywords):
        return original_inspect(
            request,
            content,
            now=lambda: reference_now,
            health_reader=referenced_health,
            **keywords,
        )

    if healthcheck:
        try:
            referenced_health()
        except service.MediaInspectorServiceError:
            return 73
        return 0

    setattr(service, "_scanner_health", referenced_health)
    setattr(service, "inspect_request", referenced_inspect)
    sys.argv = [sys.argv[0]]
    return service.main()


if __name__ == "__main__":
    raise SystemExit(main())
