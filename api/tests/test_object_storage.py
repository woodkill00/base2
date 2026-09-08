import io
from types import SimpleNamespace

import pytest

from api.services.object_storage import ObjectStorageError, S3ObjectStore


class Client:
    def __init__(self, endpoint='https://objects.example.net'):
        self.values = {}
        self.meta = SimpleNamespace(endpoint_url=endpoint)

    def put_object(self, **kwargs):
        self.values[(kwargs['Bucket'], kwargs['Key'])] = kwargs

    def get_object(self, **kwargs):
        return {'Body': io.BytesIO(self.values[(kwargs['Bucket'], kwargs['Key'])]['Body'])}

    def delete_object(self, **kwargs):
        del self.values[(kwargs['Bucket'], kwargs['Key'])]


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
