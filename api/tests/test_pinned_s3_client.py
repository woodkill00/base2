import hashlib
import io
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from api.services.pinned_s3_client import PinnedS3Client, PinnedS3Error


def test_client_connects_to_pinned_address_while_retaining_tls_hostname():
    raw = MagicMock()
    context = MagicMock()
    wrapped = MagicMock()
    context.wrap_socket.return_value = wrapped
    with (
        patch('api.services.pinned_s3_client.ssl.create_default_context', return_value=context),
        patch(
            'api.services.pinned_s3_client.socket.create_connection', return_value=raw
        ) as connect,
    ):
        from api.services.pinned_s3_client import _PinnedHTTPSConnection

        connection = _PinnedHTTPSConnection(
            'objects.example.net', address='93.184.216.34', port=443, timeout=4
        )
        connection.connect()
    connect.assert_called_once_with(('93.184.216.34', 443), 4)
    context.wrap_socket.assert_called_once_with(raw, server_hostname='objects.example.net')
    assert connection.sock is wrapped


def test_sigv4_client_exposes_exact_pin_attestation():
    client = PinnedS3Client(
        endpoint='https://objects.example.net',
        region='fra1',
        access_key='access-key',
        secret_key='secret-key',
        addresses={'93.184.216.34'},
    )
    assert client.pinned_addresses == frozenset({'93.184.216.34'})
    assert client.tls_server_name == 'objects.example.net'


def client() -> PinnedS3Client:
    return PinnedS3Client(
        endpoint='https://objects.example.net',
        region='fra1',
        access_key='access-key',
        secret_key='secret-key',
        addresses={'93.184.216.34', '93.184.216.35'},
    )


@pytest.mark.parametrize(
    'overrides',
    [
        {'endpoint': 'http://objects.example.net'},
        {'endpoint': 'https://objects.example.net/path'},
        {'region': ''},
        {'access_key': ''},
        {'secret_key': ''},
        {'addresses': set()},
        {'timeout_seconds': 0},
        {'timeout_seconds': 61},
    ],
)
def test_client_rejects_invalid_transport_configuration(overrides):
    values = {
        'endpoint': 'https://objects.example.net',
        'region': 'fra1',
        'access_key': 'access-key',
        'secret_key': 'secret-key',
        'addresses': {'93.184.216.34'},
        'timeout_seconds': 10,
        **overrides,
    }
    with pytest.raises(PinnedS3Error, match='configuration_invalid'):
        PinnedS3Client(**values)


def test_signature_is_deterministic_and_binds_every_header():
    value = client()
    now = datetime(2026, 9, 8, 12, 30, tzinfo=UTC)
    first = value._signature(
        method='PUT',
        path='/bucket/tenant/object',
        headers={
            'Host': 'objects.example.net',
            'x-amz-date': '20260908T123000Z',
            'x-amz-content-sha256': hashlib.sha256(b'payload').hexdigest(),
        },
        payload_hash=hashlib.sha256(b'payload').hexdigest(),
        now=now,
        query='versionId=version-1',
    )
    second = value._signature(
        method='PUT',
        path='/bucket/tenant/object',
        headers={
            'x-amz-content-sha256': hashlib.sha256(b'payload').hexdigest(),
            'Host': 'objects.example.net',
            'x-amz-date': '20260908T123000Z',
        },
        payload_hash=hashlib.sha256(b'payload').hexdigest(),
        now=now,
        query='versionId=version-1',
    )
    assert first == second
    assert 'Credential=access-key/20260908/fra1/s3/aws4_request' in first
    assert 'SignedHeaders=host;x-amz-content-sha256;x-amz-date' in first


def test_request_uses_pinned_addresses_and_returns_bounded_response():
    response = MagicMock(status=200)
    response.read.return_value = b'payload'
    response.getheaders.return_value = [('ETag', 'digest')]
    failed = MagicMock()
    failed.request.side_effect = OSError('first address unavailable')
    succeeded = MagicMock()
    succeeded.getresponse.return_value = response
    with patch(
        'api.services.pinned_s3_client._PinnedHTTPSConnection',
        side_effect=[failed, succeeded],
    ) as connection:
        headers, body = client()._request(
            'PUT', bucket='base2-media', key='tenant one/object', body=b'payload'
        )
    assert connection.call_count == 2
    assert failed.close.called and succeeded.close.called
    assert succeeded.request.call_args.args[:2] == ('PUT', '/base2-media/tenant%20one/object')
    assert headers == {'etag': 'digest'} and body == b'payload'


def test_request_rejects_provider_status_oversize_and_unavailable_transport():
    status_response = MagicMock(status=503)
    status_response.read.return_value = b'no'
    status_response.getheaders.return_value = []
    status_connection = MagicMock()
    status_connection.getresponse.return_value = status_response
    with (
        patch(
            'api.services.pinned_s3_client._PinnedHTTPSConnection',
            return_value=status_connection,
        ),
        pytest.raises(PinnedS3Error, match='provider_status:503'),
    ):
        client()._request('GET', bucket='base2-media', key='tenant/object')

    large_response = MagicMock(status=200)
    large_response.read.return_value = b'x' * (100 * 1024 * 1024 + 1)
    large_connection = MagicMock()
    large_connection.getresponse.return_value = large_response
    one_address = client()
    one_address.pinned_addresses = frozenset({'93.184.216.34'})
    with (
        patch(
            'api.services.pinned_s3_client._PinnedHTTPSConnection',
            return_value=large_connection,
        ),
        pytest.raises(PinnedS3Error, match='response_too_large'),
    ):
        one_address._request('GET', bucket='base2-media', key='tenant/object')

    unavailable = MagicMock()
    unavailable.request.side_effect = OSError('offline')
    with (
        patch('api.services.pinned_s3_client._PinnedHTTPSConnection', return_value=unavailable),
        pytest.raises(PinnedS3Error, match='provider_unavailable'),
    ):
        one_address._request('DELETE', bucket='base2-media', key='tenant/object')


def test_public_object_methods_apply_security_headers_versions_and_adapt_responses():
    value = client()
    with patch.object(
        value,
        '_request',
        return_value=({'etag': 'quoted', 'x-amz-version-id': 'version-1'}, b''),
    ) as request:
        assert value.put_object(
            Bucket='base2-media',
            Key='tenant/object',
            Body=b'payload',
            ContentType='image/png',
            Metadata={'Sha256': 'a' * 64},
            IfNoneMatch='*',
        ) == {'ETag': 'quoted', 'VersionId': 'version-1'}
    sent_headers = request.call_args.kwargs['headers']
    assert sent_headers['x-amz-server-side-encryption'] == 'AES256'
    assert sent_headers['Cache-Control'] == 'private,no-store'
    assert sent_headers['x-amz-meta-sha256'] == 'a' * 64
    assert sent_headers['If-None-Match'] == '*'

    with patch.object(
        value,
        '_request',
        return_value=({'x-amz-meta-sha256': 'a', 'x-amz-version-id': 'version-1'}, b'data'),
    ) as request:
        result = value.get_object(Bucket='base2-media', Key='tenant/object', VersionId='version-1')
    assert isinstance(result['Body'], io.BytesIO)
    assert result['Body'].read() == b'data'
    assert result['VersionId'] == 'version-1'
    assert request.call_args.kwargs['query'] == {'versionId': 'version-1'}

    with patch.object(value, '_request', return_value=({}, b'')) as request:
        assert (
            value.delete_object(Bucket='base2-media', Key='tenant/object', VersionId='version-1')
            == {}
        )
    assert request.call_args.args == ('DELETE',)
    assert request.call_args.kwargs['query'] == {'versionId': 'version-1'}

    with patch.object(value, '_request', return_value=({}, b'')) as request:
        assert value.head_bucket(Bucket='base2-media') == {
            'ResponseMetadata': {'HTTPStatusCode': 200},
            'VersionId': '',
        }
    assert request.call_args.args == ('HEAD',)
