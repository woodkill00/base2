import asyncio

import pytest

from api.security.upload_capacity import UploadCapacityError, upload_completion_slot


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
