"""Minimal SigV4 S3 client whose TLS socket is pinned to prevalidated addresses."""

from __future__ import annotations

import hashlib
import hmac
import http.client
import io
import socket
import ssl
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote, urlparse


class PinnedS3Error(ValueError):
    pass


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, *, address: str, port: int, timeout: float):
        context = ssl.create_default_context()
        super().__init__(hostname, port=port, timeout=timeout, context=context)
        self._address = address
        self._ssl_context = context

    def connect(self) -> None:
        raw = socket.create_connection((self._address, self.port), self.timeout)
        try:
            self.sock = self._ssl_context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


class PinnedS3Client:
    """Path-style S3 operations with hostname verification and a pinned IP set."""

    def __init__(
        self,
        *,
        endpoint: str,
        region: str,
        access_key: str,
        secret_key: str,
        addresses: set[str],
        timeout_seconds: float = 10,
    ):
        parsed = urlparse(endpoint)
        if (
            parsed.scheme != 'https'
            or parsed.path not in {'', '/'}
            or not parsed.hostname
            or not region
            or not access_key
            or not secret_key
            or not addresses
            or not 1 <= timeout_seconds <= 60
        ):
            raise PinnedS3Error('object:client_configuration_invalid')
        self.meta = SimpleNamespace(endpoint_url=endpoint.rstrip('/'))
        self.hostname = parsed.hostname
        self.port = parsed.port or 443
        self.region = region
        self._access_key = access_key
        self._secret_key = secret_key
        self.pinned_addresses = frozenset(addresses)
        self.tls_server_name = self.hostname
        self._timeout = timeout_seconds

    @staticmethod
    def _hmac(key: bytes, value: str) -> bytes:
        return hmac.new(key, value.encode(), hashlib.sha256).digest()

    def _signature(
        self, *, method: str, path: str, headers: dict[str, str], payload_hash: str, now: datetime
    ) -> str:
        lowered = {name.lower(): ' '.join(value.strip().split()) for name, value in headers.items()}
        names = ';'.join(sorted(lowered))
        canonical_headers = ''.join(f'{name}:{lowered[name]}\n' for name in sorted(lowered))
        canonical_request = '\n'.join((method, path, '', canonical_headers, names, payload_hash))
        stamp, moment = now.strftime('%Y%m%d'), now.strftime('%Y%m%dT%H%M%SZ')
        scope = f'{stamp}/{self.region}/s3/aws4_request'
        to_sign = '\n'.join(
            (
                'AWS4-HMAC-SHA256',
                moment,
                scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            )
        )
        date_key = self._hmac(('AWS4' + self._secret_key).encode(), stamp)
        region_key = self._hmac(date_key, self.region)
        service_key = self._hmac(region_key, 's3')
        signing_key = self._hmac(service_key, 'aws4_request')
        signature = hmac.new(signing_key, to_sign.encode(), hashlib.sha256).hexdigest()
        return f'AWS4-HMAC-SHA256 Credential={self._access_key}/{scope}, SignedHeaders={names}, Signature={signature}'

    def _request(
        self,
        method: str,
        *,
        bucket: str,
        key: str,
        body: bytes = b'',
        headers: dict[str, str] | None = None,
    ) -> tuple[dict[str, str], bytes]:
        path = f"/{quote(bucket, safe='')}/{quote(key, safe='/')}"
        current = datetime.now(UTC)
        payload_hash = hashlib.sha256(body).hexdigest()
        request_headers = {
            'Host': self.hostname if self.port == 443 else f'{self.hostname}:{self.port}',
            'x-amz-content-sha256': payload_hash,
            'x-amz-date': current.strftime('%Y%m%dT%H%M%SZ'),
            **(headers or {}),
        }
        request_headers['Authorization'] = self._signature(
            method=method,
            path=path,
            headers=request_headers,
            payload_hash=payload_hash,
            now=current,
        )
        last_error: Exception | None = None
        for address in sorted(self.pinned_addresses):
            connection = _PinnedHTTPSConnection(
                self.hostname, address=address, port=self.port, timeout=self._timeout
            )
            try:
                connection.request(method, path, body=body or None, headers=request_headers)
                response = connection.getresponse()
                content = response.read(100 * 1024 * 1024 + 1)
                if len(content) > 100 * 1024 * 1024:
                    raise PinnedS3Error('object:response_too_large')
                if not 200 <= response.status < 300:
                    raise PinnedS3Error(f'object:provider_status:{response.status}')
                return {name.lower(): value for name, value in response.getheaders()}, content
            except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
                last_error = exc
            finally:
                connection.close()
        raise PinnedS3Error('object:provider_unavailable') from last_error

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        headers = {
            'Content-Type': str(kwargs.get('ContentType', 'application/octet-stream')),
            'Cache-Control': str(kwargs.get('CacheControl', 'private,no-store')),
            'x-amz-server-side-encryption': str(kwargs.get('ServerSideEncryption', 'AES256')),
        }
        for name, value in dict(kwargs.get('Metadata', {})).items():
            headers[f'x-amz-meta-{name.lower()}'] = str(value)
        response_headers, _body = self._request(
            'PUT',
            bucket=str(kwargs['Bucket']),
            key=str(kwargs['Key']),
            body=bytes(kwargs['Body']),
            headers=headers,
        )
        return {'ETag': response_headers.get('etag', '')}

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        headers, body = self._request('GET', bucket=str(kwargs['Bucket']), key=str(kwargs['Key']))
        return {'Body': io.BytesIO(body), 'Metadata': headers}

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        self._request('DELETE', bucket=str(kwargs['Bucket']), key=str(kwargs['Key']))
        return {}
