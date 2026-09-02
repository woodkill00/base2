import os
import base64

import pytest

from api.services.content_workspace_storage import (
    ArtifactIntegrityError,
    PrivateArtifactStore,
    configured_artifact_store,
)


def test_private_store_encrypts_content_and_returns_only_content_addressed_reference(tmp_path):
    store = PrivateArtifactStore(tmp_path / 'workspace', key=b'k' * 32)
    stored = store.put(
        namespace='media', site_id='site-a', object_id='asset-104', content=b'private payload'
    )

    assert stored.sha256 == '074c7c3240967a181b8369139c18a1c2bfd46b4ab89d122b49b555f1270f272c'
    assert stored.byte_size == len(b'private payload')
    assert stored.object_key == 'media/site-a/asset-104.bin'
    path = tmp_path / 'workspace' / stored.object_key
    assert path.read_bytes() != b'private payload'
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert store.get(stored.object_key, expected_sha256=stored.sha256) == b'private payload'


def test_private_store_replay_is_noop_and_conflicting_overwrite_fails_closed(tmp_path):
    store = PrivateArtifactStore(tmp_path / 'workspace', key=b'k' * 32)
    first = store.put(
        namespace='imports', site_id='site-a', object_id='job-104', content=b'first'
    )
    replay = store.put(
        namespace='imports', site_id='site-a', object_id='job-104', content=b'first'
    )
    assert replay == first
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_conflict'):
        store.put(namespace='imports', site_id='site-a', object_id='job-104', content=b'second')


def test_private_store_rejects_traversal_symlinks_tamper_and_cross_context_reads(tmp_path):
    store = PrivateArtifactStore(tmp_path / 'workspace', key=b'k' * 32)
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_key_invalid'):
        store.put(namespace='../escape', site_id='site-a', object_id='x', content=b'x')

    stored = store.put(namespace='exports', site_id='site-a', object_id='job-104', content=b'x')
    path = tmp_path / 'workspace' / stored.object_key
    path.write_bytes(path.read_bytes()[:-1] + b'!')
    with pytest.raises(ArtifactIntegrityError, match='content_integrity_failed'):
        store.get(stored.object_key, expected_sha256=stored.sha256)
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_key_invalid'):
        store.get('../outside.bin', expected_sha256=stored.sha256)

    target = tmp_path / 'target'
    target.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_root_invalid'):
        PrivateArtifactStore(link, key=b'k' * 32)


def test_private_store_requires_exact_key_and_bounded_nonempty_content(tmp_path):
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_key_invalid'):
        PrivateArtifactStore(tmp_path / 'workspace', key=b'short')
    store = PrivateArtifactStore(tmp_path / 'workspace', key=b'k' * 32, max_bytes=4)
    for content in (b'', b'12345'):
        with pytest.raises(ArtifactIntegrityError, match='content_limit_exceeded'):
            store.put(namespace='media', site_id='site-a', object_id='x', content=content)


def test_configured_store_requires_absolute_root_and_urlsafe_32_byte_key(tmp_path):
    encoded = base64.urlsafe_b64encode(b'k' * 32).decode()
    assert isinstance(
        configured_artifact_store(root=str(tmp_path / 'workspace'), encoded_key=encoded),
        PrivateArtifactStore,
    )
    for root, key in [('relative', encoded), (str(tmp_path / 'workspace'), 'invalid')]:
        with pytest.raises(
            ArtifactIntegrityError, match='content_artifact_configuration_invalid'
        ):
            configured_artifact_store(root=root, encoded_key=key)
