import asyncio

import pytest

from api.security.upload_capacity import (
    DOWNLOAD_SLOTS_PER_PROCESS,
    MAX_API_WORKERS,
    MAX_DOWNLOAD_MEMORY_BUDGET_BYTES,
    MAX_DOWNLOAD_OBJECT_BYTES,
    MAX_DOWNLOAD_RESIDENT_COPIES,
    DownloadCapacityError,
    UploadBodyLimitError,
    UploadBodyTimeoutError,
    UploadCapacityError,
    download_delivery_slot,
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


@pytest.mark.asyncio
async def test_download_materialization_has_one_slot_and_bounded_waiters():
    entered = 0
    both_entered = asyncio.Event()
    release = asyncio.Event()

    async def holder():
        nonlocal entered
        async with download_delivery_slot():
            entered += 1
            both_entered.set()
            await release.wait()

    tasks = [asyncio.create_task(holder())]
    await both_entered.wait()
    try:
        with pytest.raises(DownloadCapacityError, match='download_capacity_exhausted'):
            async with download_delivery_slot(timeout_seconds=0.01):
                raise AssertionError('third materialization was admitted')
    finally:
        release.set()
        await asyncio.gather(*tasks)


def test_download_and_export_rate_limits_are_explicit(monkeypatch):
    for scope in (
        'media_download',
        'media_download_tenant',
        'media_export_create',
        'media_export_tenant',
    ):
        monkeypatch.delenv(f'RATE_LIMIT_{scope.upper()}_WINDOW_MS', raising=False)
        monkeypatch.delenv(f'RATE_LIMIT_{scope.upper()}_MAX_REQUESTS', raising=False)
    assert rate_limit._limit_for_scope('media_download') == (60_000, 12)
    assert rate_limit._limit_for_scope('media_download_tenant') == (60_000, 60)
    assert rate_limit._limit_for_scope('media_export_create') == (60_000, 5)
    assert rate_limit._limit_for_scope('media_export_tenant') == (60_000, 20)


def test_download_memory_budget_is_coupled_to_production_workers_and_policy():
    from api.services.media_library_policy import DEFAULT_POLICY

    assert DOWNLOAD_SLOTS_PER_PROCESS == 1
    assert MAX_API_WORKERS == 2
    assert MAX_DOWNLOAD_OBJECT_BYTES == DEFAULT_POLICY['maximumObjectBytes'] == 25 * 1024 * 1024
    assert MAX_DOWNLOAD_RESIDENT_COPIES == 3
    assert MAX_DOWNLOAD_MEMORY_BUDGET_BYTES == 150 * 1024 * 1024
    entrypoint = (__import__('pathlib').Path(__file__).parents[1] / 'entrypoint.sh').read_text()
    assert 'WORKERS > 2' in entrypoint
