"""Process-wide admission for memory-bearing upload completion work."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncIterable
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class UploadCapacityError(RuntimeError):
    pass


class UploadBodyLimitError(RuntimeError):
    pass


class UploadBodyTimeoutError(RuntimeError):
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


async def read_bounded_upload(
    chunks: AsyncIterable[bytes],
    *,
    maximum_bytes: int,
    idle_timeout_seconds: float = 5.0,
    total_timeout_seconds: float = 30.0,
) -> bytes:
    """Spool one body with fixed byte, idle, and total-time boundaries."""
    if (
        not isinstance(maximum_bytes, int)
        or isinstance(maximum_bytes, bool)
        or not 1 <= maximum_bytes <= 25 * 1024 * 1024
        or not 0.01 <= idle_timeout_seconds <= 30.0
        or not idle_timeout_seconds <= total_timeout_seconds <= 120.0
    ):
        raise UploadCapacityError('upload_capacity_invalid')
    received = 0
    iterator = aiter(chunks)
    try:
        async with asyncio.timeout(total_timeout_seconds):
            with tempfile.SpooledTemporaryFile(
                max_size=min(maximum_bytes, 1024 * 1024), mode='w+b'
            ) as stream:
                while True:
                    try:
                        chunk = await asyncio.wait_for(
                            anext(iterator), timeout=idle_timeout_seconds
                        )
                    except StopAsyncIteration:
                        break
                    received += len(chunk)
                    if received > maximum_bytes:
                        raise UploadBodyLimitError('upload_body_limit_exceeded')
                    stream.write(chunk)
                stream.seek(0)
                return stream.read(maximum_bytes + 1)
    except TimeoutError as exc:
        raise UploadBodyTimeoutError('upload_body_timeout') from exc
