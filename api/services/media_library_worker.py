"""Fixed media worker dispatcher with no command, path, URL, or code authority."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable

from api.services.media_library_operations import build_export, destructive_preview
from api.services.media_library_processor import generate_media_preview


class MediaWorkerError(ValueError):
    pass


@dataclass(frozen=True)
class WorkerResult:
    kind: str
    status: str
    safe_code: str
    output_sha256: str
    output: Any = None


def _keys(payload: dict[str, Any], expected: set[str]) -> None:
    if not isinstance(payload, dict) or set(payload) != expected:
        raise MediaWorkerError('media_worker_payload_invalid')


def _inspect(payload: dict[str, Any]) -> WorkerResult:
    _keys(payload, {'content', 'claimedType', 'detectedType', 'scannerDecision'})
    content = payload['content']
    if (
        not isinstance(content, bytes)
        or not content
        or payload['claimedType'] != payload['detectedType']
        or payload['scannerDecision'] not in {'clean', 'rejected'}
    ):
        raise MediaWorkerError('media_inspection_rejected')
    if payload['scannerDecision'] != 'clean':
        raise MediaWorkerError('media_inspection_rejected')
    return WorkerResult(
        'inspect', 'completed', 'media_inspection_accepted', hashlib.sha256(content).hexdigest()
    )


def _derive(payload: dict[str, Any]) -> WorkerResult:
    _keys(payload, {'content', 'mediaType'})
    preview = generate_media_preview(content=payload['content'], media_type=payload['mediaType'])
    return WorkerResult('derive', 'completed', 'media_derivative_ready', preview.sha256, preview)


def _export(payload: dict[str, Any]) -> WorkerResult:
    _keys(payload, {'rows', 'outputFormat', 'fields'})
    output = build_export(
        payload['rows'], output_format=payload['outputFormat'], fields=tuple(payload['fields'])
    )
    return WorkerResult(
        'export', 'completed', 'media_export_ready', hashlib.sha256(output).hexdigest(), output
    )


def _reconcile(payload: dict[str, Any]) -> WorkerResult:
    _keys(payload, {'storage', 'prefix', 'expectedKeys'})
    unknown = payload['storage'].reconcile(
        prefix=payload['prefix'], expected_keys=frozenset(payload['expectedKeys'])
    )
    encoded = '\n'.join(unknown).encode()
    return WorkerResult(
        'reconcile',
        'completed',
        'media_reconcile_complete',
        hashlib.sha256(encoded).hexdigest(),
        unknown,
    )


def _purge(payload: dict[str, Any]) -> WorkerResult:
    _keys(payload, {'storage', 'assetId', 'references', 'holds', 'objects'})
    preview = destructive_preview(
        asset_id=payload['assetId'],
        references=payload['references'],
        holds=payload['holds'],
        objects=payload['objects'],
    )
    if not preview['allowed']:
        raise MediaWorkerError('media_purge_blocked')
    deleted = []
    for item in payload['objects']:
        if set(item) != {'key', 'sha256'}:
            raise MediaWorkerError('media_worker_payload_invalid')
        if payload['storage'].delete(
            key=item['key'], expected_sha256=item['sha256'], missing_ok=True
        ):
            deleted.append(item['key'])
    digest = hashlib.sha256('\n'.join(sorted(deleted)).encode()).hexdigest()
    return WorkerResult('purge', 'completed', 'media_purge_complete', digest, tuple(deleted))


HANDLERS: dict[str, Callable[[dict[str, Any]], WorkerResult]] = {
    'inspect': _inspect,
    'derive': _derive,
    'export': _export,
    'reconcile': _reconcile,
    'purge': _purge,
}


def dispatch_fixed_media_job(kind: str, payload: dict[str, Any]) -> WorkerResult:
    try:
        handler = HANDLERS[kind]
    except (KeyError, TypeError) as exc:
        raise MediaWorkerError('media_worker_kind_invalid') from exc
    try:
        return handler(payload)
    except MediaWorkerError:
        raise
    except ValueError as exc:
        code = str(exc)
        if code.startswith('media_'):
            raise MediaWorkerError(code) from exc
        raise MediaWorkerError('media_worker_dependency_failed') from exc
    except Exception as exc:
        raise MediaWorkerError('media_worker_dependency_failed') from exc
