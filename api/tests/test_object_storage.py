import io
from types import SimpleNamespace

import pytest

from api.services.object_storage import ObjectStorageError, S3ObjectStore
from api.services.content_workspace_storage import S3ArtifactStore


class Client:
    def __init__(self, endpoint='https://objects.example.net'):
        self.values = {}
        self.meta = SimpleNamespace(endpoint_url=endpoint)
        self.pinned_addresses = frozenset({'93.184.216.34'})
        self.tls_server_name = 'objects.example.net'

    def put_object(self, **kwargs):
        self.values[(kwargs['Bucket'], kwargs['Key'])] = kwargs
        return {'VersionId': 'version-1'}

    def get_object(self, **kwargs):
        return {
            'Body': io.BytesIO(self.values[(kwargs['Bucket'], kwargs['Key'])]['Body']),
            'VersionId': kwargs.get('VersionId', 'version-1'),
        }

    def delete_object(self, **kwargs):
        del self.values[(kwargs['Bucket'], kwargs['Key'])]

    def head_bucket(self, **kwargs):
        return {'ResponseMetadata': {'HTTPStatusCode': 200}}


def test_s3_store_is_https_allowlisted_tenant_keyed_encrypted_and_integrity_checked():
    client = Client()
    store = S3ObjectStore(
        endpoint='https://objects.example.net',
        bucket='base2-media',
        client=client,
        allowed_hosts={'objects.example.net'},
        resolver=lambda *_: [(None, None, None, None, ('93.184.216.34', 443))],
    )
    receipt = store.put(
        tenant_id='tenant-one', namespace='media', object_id='asset-1', content=b'hello'
    )
    request = client.values[(receipt.bucket, receipt.key)]
    assert receipt.key == 'tenant-one/media/asset-1'
    assert request['ServerSideEncryption'] == 'AES256'
    assert request['CacheControl'] == 'private,no-store'
    assert request['IfNoneMatch'] == '*'
    assert receipt.version_id == 'version-1'
    assert store.get(tenant_id='tenant-one', receipt=receipt) == b'hello'
    with pytest.raises(ObjectStorageError, match='ownership'):
        store.get(tenant_id='tenant-two', receipt=receipt)
    client.values[(receipt.bucket, receipt.key)]['Body'] = b'tampered'
    with pytest.raises(ObjectStorageError, match='integrity'):
        store.get(tenant_id='tenant-one', receipt=receipt)


@pytest.mark.parametrize(
    'endpoint', ['http://objects.example.net', 'https://127.0.0.1', 'https://evil.test']
)
def test_s3_store_rejects_insecure_private_and_unapproved_origins(endpoint):
    with pytest.raises(ObjectStorageError, match='configuration'):
        S3ObjectStore(
            endpoint=endpoint,
            bucket='base2-media',
            client=Client(),
            allowed_hosts={'objects.example.net'},
            resolver=lambda *_: [(None, None, None, None, ('93.184.216.34', 443))],
        )


def test_s3_store_rejects_allowlisted_host_resolving_private():
    with pytest.raises(ObjectStorageError, match='configuration'):
        S3ObjectStore(
            endpoint='https://objects.example.net',
            bucket='base2-media',
            client=Client(),
            allowed_hosts={'objects.example.net'},
            resolver=lambda *_: [(None, None, None, None, ('169.254.169.254', 443))],
        )


def test_s3_store_rechecks_dns_and_rejects_client_endpoint_mismatch():
    answers = ['93.184.216.34']

    def resolver(*_):
        return [(None, None, None, None, (answers[-1], 443))]

    with pytest.raises(ObjectStorageError, match='endpoint_mismatch'):
        S3ObjectStore(
            endpoint='https://objects.example.net',
            bucket='base2-media',
            client=Client('https://169.254.169.254'),
            allowed_hosts={'objects.example.net'},
            resolver=resolver,
        )
    store = S3ObjectStore(
        endpoint='https://objects.example.net',
        bucket='base2-media',
        client=Client(),
        allowed_hosts={'objects.example.net'},
        resolver=resolver,
    )
    answers.append('127.0.0.1')
    with pytest.raises(ObjectStorageError, match='configuration'):
        store.put(tenant_id='tenant-one', namespace='media', object_id='asset-1', content=b'x')


def test_s3_store_rejects_client_that_will_resolve_hostname_again():
    client = Client()
    client.pinned_addresses = frozenset()
    with pytest.raises(ObjectStorageError, match='client_not_pinned'):
        S3ObjectStore(
            endpoint='https://objects.example.net',
            bucket='base2-media',
            client=client,
            allowed_hosts={'objects.example.net'},
            resolver=lambda *_: [(None, None, None, None, ('93.184.216.34', 443))],
        )


def test_media_artifact_adapter_uses_tenant_owned_s3_keys():
    client = Client()
    store = S3ObjectStore(
        endpoint='https://objects.example.net',
        bucket='base2-media',
        client=client,
        allowed_hosts={'objects.example.net'},
        resolver=lambda *_: [(None, None, None, None, ('93.184.216.34', 443))],
    )
    artifacts = S3ArtifactStore(store, max_bytes=1024)
    stored = artifacts.put(
        namespace='media', site_id='tenant-one', object_id='asset-1', content=b'hello'
    )
    assert artifacts.get(stored.object_key, expected_sha256=stored.sha256) == b'hello'
    assert artifacts.delete(
        namespace='media',
        site_id='tenant-one',
        object_id='asset-1',
        object_key=stored.object_key,
        expected_sha256=stored.sha256,
    )
