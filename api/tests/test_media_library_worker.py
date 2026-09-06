from __future__ import annotations

import hashlib

import pytest

from api.services.media_library_storage import InMemoryMediaObjectStorage
from api.services.media_library_worker import MediaWorkerError, dispatch_fixed_media_job


CONTENT = b'synthetic-safe-media'
DIGEST = hashlib.sha256(CONTENT).hexdigest()
PART = f'media-parts/base2-site/{"1" * 32}/p1/{DIGEST}.bin'
OBJECT = f'media/base2-site/{"2" * 32}/v1/{DIGEST}.bin'


def test_fixed_handlers_cover_inspect_derive_export_reconcile_and_purge():
    inspected = dispatch_fixed_media_job(
        'inspect',
        {
            'content': CONTENT,
            'claimedType': 'image/png',
            'detectedType': 'image/png',
            'scannerDecision': 'clean',
        },
    )
    assert inspected.output_sha256 == DIGEST
    derived = dispatch_fixed_media_job('derive', {'content': CONTENT, 'mediaType': 'audio/mpeg'})
    assert derived.output.content.startswith(b'\x89PNG')
    exported = dispatch_fixed_media_job(
        'export', {'rows': [{'id': 'one'}], 'outputFormat': 'json', 'fields': ['id']}
    )
    assert exported.output == b'[{"id":"one"}]'

    store = InMemoryMediaObjectStorage()
    store.put_part(key=PART, content=CONTENT)
    store.complete(key=OBJECT, parts=(PART,), expected_sha256=DIGEST)
    reconciled = dispatch_fixed_media_job(
        'reconcile', {'storage': store, 'prefix': 'media/base2-site/', 'expectedKeys': []}
    )
    assert reconciled.output == (OBJECT,)
    purged = dispatch_fixed_media_job(
        'purge',
        {
            'storage': store,
            'assetId': 'asset-1',
            'references': [],
            'holds': [],
            'objects': [{'key': OBJECT, 'sha256': DIGEST}],
        },
    )
    assert purged.output == (OBJECT,)


def test_dispatch_rejects_arbitrary_kind_fields_and_dependency_detail():
    with pytest.raises(MediaWorkerError, match='kind_invalid'):
        dispatch_fixed_media_job('shell', {'command': 'rm -rf /'})
    with pytest.raises(MediaWorkerError, match='payload_invalid'):
        dispatch_fixed_media_job(
            'inspect',
            {
                'content': CONTENT,
                'claimedType': 'image/png',
                'detectedType': 'image/png',
                'scannerDecision': 'clean',
                'command': 'unexpected',
            },
        )
    with pytest.raises(MediaWorkerError, match='media_inspection_rejected'):
        dispatch_fixed_media_job(
            'inspect',
            {
                'content': CONTENT,
                'claimedType': 'image/png',
                'detectedType': 'image/jpeg',
                'scannerDecision': 'clean',
            },
        )
