"""Process-wide admission for memory-bearing upload completion work."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class UploadCapacityError(RuntimeError):
    pass


# Each ASGI process may materialize at most one policy-bounded object while
# validating and encrypting it. Additional requests remain under server/socket
# backpressure and fail quickly instead of accumulating request bodies in RAM.
_completion_slot = asyncio.BoundedSemaphore(1)


@asynccontextmanager
async def upload_completion_slot(*, timeout_seconds: float = 1.0) -> AsyncIterator[None]:
    if not 0.01 <= timeout_seconds <= 5.0:
        raise UploadCapacityError('upload_capacity_invalid')
    acquired = False
    try:
        await asyncio.wait_for(_completion_slot.acquire(), timeout=timeout_seconds)
        acquired = True
        yield
    except TimeoutError as exc:
        raise UploadCapacityError('upload_capacity_exhausted') from exc
    finally:
        if acquired:
            _completion_slot.release()
