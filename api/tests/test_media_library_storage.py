from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from api.services.media_library_storage import (
    InMemoryMediaObjectStorage,
    MediaStorageError,
    RuntimeMediaObjectStorage,
)


CONTENT = b'synthetic-safe-media'
DIGEST = hashlib.sha256(CONTENT).hexdigest()
PART = f'media-parts/base2-site/{"1" * 32}/p1/{DIGEST}.bin'
OBJECT = f'media/base2-site/{"2" * 32}/v1/{DIGEST}.bin'
NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)


def test_fake_supports_full_exact_owned_contract_without_etag_confusion():
    store = InMemoryMediaObjectStorage()
    part = store.put_part(key=PART, content=CONTENT)
    assert part.sha256 == DIGEST and DIGEST not in part.transport_etag
    completed = store.complete(key=OBJECT, parts=(PART,), expected_sha256=DIGEST)
    assert store.read(key=OBJECT, expected_sha256=DIGEST) == CONTENT
    assert store.head(key=OBJECT) == completed
    assert store.list_owned(prefix='media/base2-site/') == (completed,)
    assert store.reconcile(prefix='media/base2-site/', expected_keys=frozenset()) == (OBJECT,)
    grant = store.sign(
        key=OBJECT,
        expected_sha256=DIGEST,
        method='GET',
        audience_ref='user:owner',
        observed_at=NOW,
        lifetime=timedelta(minutes=5),
    )
    assert OBJECT not in grant.url and grant.expires_at == NOW + timedelta(minutes=5)
    assert store.delete(key=OBJECT, expected_sha256=DIGEST)
    assert not store.delete(key=OBJECT, expected_sha256=DIGEST, missing_ok=True)


def test_fake_rejects_scope_digest_mutability_and_unsafe_reconciliation():
    store = InMemoryMediaObjectStorage()
    with pytest.raises(MediaStorageError, match='key_invalid'):
        store.put_part(key='../../escape', content=CONTENT)
    with pytest.raises(MediaStorageError, match='digest_mismatch'):
        store.put_part(key=PART.replace(DIGEST, 'a' * 64), content=CONTENT)
    store.put_part(key=PART, content=CONTENT)
    with pytest.raises(MediaStorageError, match='owner_mismatch'):
        store.reconcile(prefix='media/base2-site/', expected_keys=frozenset({PART}))
    with pytest.raises(MediaStorageError, match='grant_invalid'):
        store.sign(
            key=PART,
            expected_sha256=DIGEST,
            method='POST',
            audience_ref='user:owner',
            observed_at=NOW,
            lifetime=timedelta(minutes=5),
        )


def test_runtime_adapter_requires_secretref_and_complete_fixed_client_surface():
    with pytest.raises(MediaStorageError, match='secretref_invalid'):
        RuntimeMediaObjectStorage(client=object(), credential_ref='plaintext', bucket='safe-bucket')
    with pytest.raises(MediaStorageError, match='client_invalid'):
        RuntimeMediaObjectStorage(
            client=object(), credential_ref='secretref:base2/media-storage', bucket='safe-bucket'
        )
