import asyncio

import pytest

from api.security.upload_capacity import (
    UploadBodyLimitError,
    UploadBodyTimeoutError,
    UploadCapacityError,
    read_bounded_upload,
    upload_completion_slot,
)
from api.security import rate_limit


@pytest.mark.asyncio
async def test_upload_completion_is_single_slot_and_fails_bounded_waiters():
    entered = asyncio.Event()
    release = asyncio.Event()

    async def holder():
        async with upload_completion_slot():
            entered.set()
            await release.wait()

    task = asyncio.create_task(holder())
    await entered.wait()
    try:
        with pytest.raises(UploadCapacityError, match='upload_capacity_exhausted'):
            async with upload_completion_slot(timeout_seconds=0.01):
                raise AssertionError('capacity guard admitted a second body')
    finally:
        release.set()
        await task


@pytest.mark.asyncio
async def test_upload_completion_releases_slot_after_failure():
    with pytest.raises(RuntimeError, match='synthetic'):
        async with upload_completion_slot():
            raise RuntimeError('synthetic')
    async with upload_completion_slot(timeout_seconds=0.01):
        pass


@pytest.mark.asyncio
async def test_upload_reader_enforces_byte_idle_and_total_bounds():
    async def finite():
        yield b'ab'
        yield b'cd'

    assert await read_bounded_upload(finite(), maximum_bytes=4) == b'abcd'
    with pytest.raises(UploadBodyLimitError, match='upload_body_limit_exceeded'):
        await read_bounded_upload(finite(), maximum_bytes=3)

    async def slow():
        await asyncio.sleep(1)
        yield b'a'

    with pytest.raises(UploadBodyTimeoutError, match='upload_body_timeout'):
        await read_bounded_upload(
            slow(),
            maximum_bytes=4,
            idle_timeout_seconds=0.01,
            total_timeout_seconds=0.02,
        )


@pytest.mark.asyncio
async def test_timed_out_body_releases_completion_slot():
    async def slow():
        await asyncio.sleep(1)
        yield b'a'

    with pytest.raises(UploadBodyTimeoutError):
        async with upload_completion_slot():
            await read_bounded_upload(
                slow(),
                maximum_bytes=4,
                idle_timeout_seconds=0.01,
                total_timeout_seconds=0.02,
            )
    async with upload_completion_slot(timeout_seconds=0.01):
        pass


def test_upload_completion_has_an_explicit_conservative_rate_limit(monkeypatch):
    monkeypatch.delenv('RATE_LIMIT_MEDIA_UPLOAD_COMPLETE_WINDOW_MS', raising=False)
    monkeypatch.delenv('RATE_LIMIT_MEDIA_UPLOAD_COMPLETE_MAX_REQUESTS', raising=False)
    assert rate_limit._limit_for_scope('media_upload_complete') == (60_000, 1)
