import os
import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from api.services.content_workspace_storage import (
    ArtifactIntegrityError,
    PrivateArtifactStore,
    S3ArtifactStore,
    configured_artifact_store,
    configured_runtime_artifact_store,
    configured_s3_artifact_store,
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
    first = store.put(namespace='imports', site_id='site-a', object_id='job-104', content=b'first')
    replay = store.put(namespace='imports', site_id='site-a', object_id='job-104', content=b'first')
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
        with pytest.raises(ArtifactIntegrityError, match='content_artifact_configuration_invalid'):
            configured_artifact_store(root=root, encoded_key=key)


def test_private_store_deletes_only_exact_owned_integrity_checked_object(tmp_path):
    store = PrivateArtifactStore(tmp_path / 'workspace', key=b'k' * 32)
    stored = store.put(
        namespace='exports', site_id='site-a', object_id='job-104', content=b'private'
    )
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_owner_mismatch'):
        store.delete(
            namespace='exports',
            site_id='site-b',
            object_id='job-104',
            object_key=stored.object_key,
            expected_sha256=stored.sha256,
        )
    with pytest.raises(ArtifactIntegrityError, match='content_integrity_failed'):
        store.delete(
            namespace='exports',
            site_id='site-a',
            object_id='job-104',
            object_key=stored.object_key,
            expected_sha256='0' * 64,
        )
    assert store.delete(
        namespace='exports',
        site_id='site-a',
        object_id='job-104',
        object_key=stored.object_key,
        expected_sha256=stored.sha256,
    )
    assert not store.delete(
        namespace='exports',
        site_id='site-a',
        object_id='job-104',
        object_key=stored.object_key,
        expected_sha256=stored.sha256,
        missing_ok=True,
    )


def test_s3_store_adapts_put_get_and_exact_owned_delete():
    backend = MagicMock(bucket='base2-media')
    backend.put.return_value = SimpleNamespace(
        key='site-a/media/asset-104', sha256='a' * 64, byte_size=7
    )
    backend.get.return_value = b'payload'
    store = S3ArtifactStore(backend, max_bytes=8)
    stored = store.put(
        namespace='media', site_id='site-a', object_id='asset-104', content=b'payload'
    )
    assert stored.object_key == 'site-a/media/asset-104'
    assert store.get(stored.object_key, expected_sha256='a' * 64) == b'payload'
    assert store.delete(
        namespace='media',
        site_id='site-a',
        object_id='asset-104',
        object_key=stored.object_key,
        expected_sha256='a' * 64,
    )
    receipt = backend.delete.call_args.kwargs['receipt']
    assert receipt.tenant_id == 'site-a' and receipt.byte_size == -1


def test_s3_store_rejects_limits_bad_keys_and_backend_failures():
    backend = MagicMock(bucket='base2-media')
    store = S3ArtifactStore(backend, max_bytes=4)
    with pytest.raises(ArtifactIntegrityError, match='content_limit_exceeded'):
        store.put(namespace='media', site_id='site-a', object_id='asset-104', content=b'12345')
    backend.put.side_effect = ValueError('object:provider_unavailable')
    with pytest.raises(ArtifactIntegrityError, match='provider_unavailable'):
        store.put(namespace='media', site_id='site-a', object_id='asset-104', content=b'1234')
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_key_invalid'):
        store.get('bad-key', expected_sha256='a' * 64)
    backend.get.side_effect = ValueError('object:integrity_invalid')
    with pytest.raises(ArtifactIntegrityError, match='integrity_invalid'):
        store.get('site-a/media/asset-104', expected_sha256='a' * 64)
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_owner_mismatch'):
        store.delete(
            namespace='media',
            site_id='site-b',
            object_id='asset-104',
            object_key='site-a/media/asset-104',
            expected_sha256='a' * 64,
        )
    backend.delete.side_effect = ValueError('object:unavailable')
    assert not store.delete(
        namespace='media',
        site_id='site-a',
        object_id='asset-104',
        object_key='site-a/media/asset-104',
        expected_sha256='a' * 64,
        missing_ok=True,
    )
    with pytest.raises(ArtifactIntegrityError, match='object:unavailable'):
        store.delete(
            namespace='media',
            site_id='site-a',
            object_id='asset-104',
            object_key='site-a/media/asset-104',
            expected_sha256='a' * 64,
        )


def test_configured_s3_store_reads_private_files_and_pins_resolution(tmp_path):
    access = tmp_path / 'access-key'
    secret = tmp_path / 'secret-key'
    access.write_text('access-value', encoding='utf-8')
    secret.write_text('secret-value', encoding='utf-8')
    access.chmod(0o600)
    secret.chmod(0o600)
    resolver = MagicMock(return_value=[(2, 1, 6, '', ('93.184.216.34', 443))])
    store = configured_s3_artifact_store(
        endpoint='https://objects.example.net',
        bucket='base2-media',
        region='fra1',
        allowed_hosts={'objects.example.net'},
        access_key_file=str(access),
        secret_key_file=str(secret),
        max_bytes=1024,
        resolver=resolver,
    )
    assert isinstance(store, S3ArtifactStore)
    assert store._store._pinned_addresses == frozenset({'93.184.216.34'})


def test_configured_s3_store_rejects_unsafe_secrets_and_resolution(tmp_path):
    secret = tmp_path / 'secret-key'
    secret.write_text('secret-value', encoding='utf-8')
    secret.chmod(0o600)
    for access in ('relative', str(tmp_path / 'missing')):
        with pytest.raises(ArtifactIntegrityError, match='content_artifact_configuration_invalid'):
            configured_s3_artifact_store(
                endpoint='https://objects.example.net',
                bucket='base2-media',
                region='fra1',
                allowed_hosts={'objects.example.net'},
                access_key_file=access,
                secret_key_file=str(secret),
                max_bytes=1024,
                resolver=lambda *_args: [(2, 1, 6, '', ('93.184.216.34', 443))],
            )
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_configuration_invalid'):
        configured_s3_artifact_store(
            endpoint='https://objects.example.net',
            bucket='base2-media',
            region='fra1',
            allowed_hosts={'objects.example.net'},
            access_key_file=str(secret),
            secret_key_file=str(secret),
            max_bytes=1024,
            resolver=MagicMock(side_effect=OSError('dns unavailable')),
        )


def test_runtime_store_factory_selects_one_backend_for_all_callers(monkeypatch):
    settings = SimpleNamespace(
        CONTENT_WORKSPACE_STORAGE_BACKEND='local',
        CONTENT_WORKSPACE_STORAGE_ROOT='/private/artifacts',
        CONTENT_WORKSPACE_STORAGE_KEY='encoded',
    )
    local = MagicMock()
    monkeypatch.setattr('api.services.content_workspace_storage.configured_artifact_store', local)
    configured_runtime_artifact_store(settings, max_bytes=1024)
    assert local.call_args.kwargs['max_bytes'] == 1024

    settings.CONTENT_WORKSPACE_STORAGE_BACKEND = 's3'
    settings.CONTENT_WORKSPACE_S3_ENDPOINT = 'https://objects.example.net'
    settings.CONTENT_WORKSPACE_S3_BUCKET = 'base2-media'
    settings.CONTENT_WORKSPACE_S3_REGION = 'fra1'
    settings.CONTENT_WORKSPACE_S3_ALLOWED_HOSTS = 'objects.example.net'
    settings.CONTENT_WORKSPACE_S3_ACCESS_KEY_FILE = '/run/secrets/s3-access'
    settings.CONTENT_WORKSPACE_S3_SECRET_KEY_FILE = '/run/secrets/s3-secret'
    s3 = MagicMock()
    monkeypatch.setattr('api.services.content_workspace_storage.configured_s3_artifact_store', s3)
    configured_runtime_artifact_store(settings, max_bytes=2048)
    assert s3.call_args.kwargs['allowed_hosts'] == {'objects.example.net'}

    settings.CONTENT_WORKSPACE_STORAGE_BACKEND = 'unknown'
    with pytest.raises(ArtifactIntegrityError, match='configuration_invalid'):
        configured_runtime_artifact_store(settings, max_bytes=1024)
