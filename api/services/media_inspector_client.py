"""Fail-closed shared-spool client for the networkless media inspector."""

from __future__ import annotations
import hashlib
import json
import os
import shutil
import stat
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4
from api.services.media_inspector_receipt import (
    InspectorReceiptError,
    load_verify_key,
    verify_receipt,
)

MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_PREVIEW_BYTES = 10 * 1024 * 1024
MAX_RECEIPT_BYTES = 32 * 1024
MAX_FAILURE_CODE_BYTES = 128
INSPECTOR_FAILURE_CODES = frozenset(
    {
        'media_decoder_failed',
        'media_decoder_response_invalid',
        'media_inspection_rejected',
        'media_inspector_dependency_unavailable',
        'media_inspector_failed',
        'media_inspector_identity_unavailable',
        'media_inspector_output_invalid',
        'media_inspector_request_invalid',
        'media_integrity_failed',
        'media_scanner_identity_changed',
        'media_scanner_definitions_stale',
        'media_scanner_response_invalid',
        'media_scanner_unavailable',
    }
)


class MediaInspectorClientError(ValueError):
    pass


@dataclass(frozen=True)
class InspectedPreview:
    content: bytes
    media_type: str
    width: int | None
    height: int | None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class VerifiedInspection:
    preview: InspectedPreview
    scanner_ref: str
    definitions_at: datetime
    observed_media_type: str
    decoder_ref: str
    measurements: dict[str, int | float]
    result_sha256: str


def _write_exclusive(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _read_regular(path: Path, maximum: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= maximum:
            raise MediaInspectorClientError('media_inspector_response_invalid')
        result = stream.read(maximum + 1)
    if len(result) > maximum:
        raise MediaInspectorClientError('media_inspector_response_invalid')
    return result


def inspect_media_via_spool(
    *,
    content: bytes,
    expected_sha256: str,
    media_type: str,
    asset_id: UUID,
    object_version: int,
    observed_at: datetime,
    spool_root: str | None = None,
    encoded_verify_key: str | None = None,
    timeout_seconds: float = 55.0,
) -> VerifiedInspection:
    if (
        not isinstance(content, bytes)
        or not 1 <= len(content) <= MAX_SOURCE_BYTES
        or hashlib.sha256(content).hexdigest() != expected_sha256
    ):
        raise MediaInspectorClientError('media_integrity_failed')
    if (
        not isinstance(object_version, int)
        or isinstance(object_version, bool)
        or object_version < 1
        or not 1 <= timeout_seconds <= 60
    ):
        raise MediaInspectorClientError('media_inspector_request_invalid')
    root_value = (
        spool_root or os.getenv('MEDIA_INSPECTOR_SPOOL_ROOT') or '/var/lib/base2/media-inspector'
    )
    root = Path(root_value)
    if not root.is_absolute() or root.is_symlink():
        raise MediaInspectorClientError('media_inspector_isolation_unavailable')
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise MediaInspectorClientError('media_inspector_isolation_unavailable') from exc
    try:
        key = load_verify_key(
            encoded_verify_key
            if encoded_verify_key is not None
            else os.getenv('MEDIA_INSPECTOR_VERIFY_KEY', '')
        )
    except InspectorReceiptError as exc:
        raise MediaInspectorClientError(str(exc)) from exc
    job_id, nonce = str(uuid4()), uuid4().hex
    job = root / job_id
    try:
        job.mkdir(mode=0o700)
        request = {
            'schemaVersion': 'base2-media-inspection-request-v1',
            'jobId': job_id,
            'nonce': nonce,
            'assetId': str(asset_id),
            'objectVersion': object_version,
            'sourceSha256': expected_sha256,
            'mediaType': media_type,
        }
        _write_exclusive(job / 'content.bin', content)
        _write_exclusive(
            job / 'request.json',
            json.dumps(request, sort_keys=True, separators=(',', ':')).encode(),
        )
        _write_exclusive(job / 'ready', b'1')
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if (job / 'failed').is_file():
                try:
                    code = _read_regular(job / 'failed', MAX_FAILURE_CODE_BYTES).decode('ascii')
                except (UnicodeDecodeError, MediaInspectorClientError) as exc:
                    raise MediaInspectorClientError('media_inspector_response_invalid') from exc
                if code not in INSPECTOR_FAILURE_CODES:
                    raise MediaInspectorClientError('media_inspector_response_invalid')
                raise MediaInspectorClientError(code)
            if (job / 'complete').is_file():
                break
            time.sleep(0.05)
        else:
            raise MediaInspectorClientError('media_inspector_timeout')
        receipt = json.loads(_read_regular(job / 'receipt.json', MAX_RECEIPT_BYTES))
        payload = verify_receipt(
            receipt,
            key=key,
            expected_job_id=job_id,
            expected_nonce=nonce,
            expected_asset_id=str(asset_id),
            expected_object_version=object_version,
            expected_source_sha256=expected_sha256,
            expected_media_type=media_type,
            now=datetime.now(UTC),
        )
        preview = _read_regular(job / 'preview.bin', MAX_PREVIEW_BYTES)
        meta = payload['preview']
        if (
            len(preview) != meta['byteSize']
            or hashlib.sha256(preview).hexdigest() != meta['sha256']
        ):
            raise MediaInspectorClientError('media_inspector_preview_invalid')
        scanner, decoder = payload['scanner'], payload['decoder']
        return VerifiedInspection(
            InspectedPreview(preview, meta['mediaType'], meta['width'], meta['height']),
            f'{scanner["engine"]}:{scanner["version"]}-{scanner["definitionsVersion"]}',
            datetime.fromisoformat(scanner['definitionsAt'].replace('Z', '+00:00')).astimezone(UTC),
            payload['observedMediaType'],
            f'{decoder["name"]}:{decoder["version"]}',
            dict(payload['measurements']),
            receipt['resultSha256'],
        )
    except (OSError, json.JSONDecodeError, InspectorReceiptError) as exc:
        code = (
            str(exc)
            if isinstance(exc, InspectorReceiptError)
            else 'media_inspector_response_invalid'
        )
        raise MediaInspectorClientError(code) from exc
    finally:
        shutil.rmtree(job, ignore_errors=True)
