#!/usr/bin/env python3
"""Bounded DigitalOcean readiness polling after a paid create request."""

from __future__ import annotations

import time
from collections.abc import Callable

from azure.core.exceptions import ServiceRequestError, ServiceResponseError


class ProviderReadyError(RuntimeError):
    """A created provider resource did not reach a safe usable state."""


TERMINAL_STATES = frozenset({"archive", "deleted", "error", "failed", "off"})


def wait_for_active_public_ipv4(
    client,
    droplet_id: int,
    *,
    timeout_sec: int,
    interval_sec: int = 5,
    address_reader: Callable[[dict], str | None],
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[str, dict]:
    """Wait under one deadline for both active state and a public IPv4 address."""

    if timeout_sec < 1 or interval_sec < 1:
        raise ProviderReadyError("provider_ready_bounds_invalid")
    deadline = clock() + timeout_sec
    last_error: Exception | None = None
    while clock() <= deadline:
        try:
            response = client.droplets.get(droplet_id)
            droplet = response["droplet"]
            if not isinstance(droplet, dict):
                raise TypeError("droplet response is not an object")
            status = str(droplet.get("status") or "").strip().lower()
            if status in TERMINAL_STATES:
                raise ProviderReadyError(f"provider_ready_terminal_state:{status}")
            address = address_reader(droplet)
            if status == "active" and address:
                return address, droplet
            last_error = None
        except ProviderReadyError:
            raise
        except (
            KeyError,
            TypeError,
            ValueError,
            OSError,
            TimeoutError,
            ServiceRequestError,
            ServiceResponseError,
        ) as exc:
            last_error = exc
        remaining = deadline - clock()
        if remaining <= 0:
            break
        sleeper(min(float(interval_sec), remaining))
    suffix = ":transport_or_contract" if last_error is not None else ""
    raise ProviderReadyError(f"provider_ready_timeout{suffix}")
