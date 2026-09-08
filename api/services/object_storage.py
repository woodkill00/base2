"""Closed S3-compatible object adapter behind Base2 media contracts."""

from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

BUCKET = re.compile(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$')
OBJECT = re.compile(r'^[a-z0-9][a-z0-9_/-]{0,499}$')


class ObjectStorageError(ValueError):
    pass


class S3Client(Protocol):
    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...
    def delete_object(self, **kwargs: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ObjectReceipt:
    tenant_id: str
    bucket: str
    key: str
    sha256: str
    byte_size: int


class S3ObjectStore:
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        client: S3Client,
        allowed_hosts: set[str],
        resolver: Any = socket.getaddrinfo,
    ):
        parsed = urlparse(endpoint)
        if (
            parsed.scheme != 'https'
            or parsed.path not in {'', '/'}
            or parsed.query
            or parsed.fragment
            or parsed.hostname not in allowed_hosts
            or not BUCKET.fullmatch(bucket)
        ):
            raise ObjectStorageError('object:configuration_invalid')
        try:
            if parsed.hostname and ipaddress.ip_address(parsed.hostname).is_private:
                raise ObjectStorageError('object:configuration_invalid')
        except ValueError:
            pass
        port = parsed.port or 443
        try:
            addresses = {item[4][0] for item in resolver(parsed.hostname, port)}
            if not addresses or any(
                not ipaddress.ip_address(value).is_global for value in addresses
            ):
                raise ObjectStorageError('object:configuration_invalid')
        except (OSError, TypeError, ValueError) as exc:
            raise ObjectStorageError('object:configuration_invalid') from exc
        client_endpoint = str(getattr(getattr(client, 'meta', None), 'endpoint_url', ''))
        if client_endpoint.rstrip('/') != endpoint.rstrip('/'):
            raise ObjectStorageError('object:client_endpoint_mismatch')
        self.endpoint, self.bucket, self.client = endpoint.rstrip('/'), bucket, client
        self._resolver, self._hostname, self._port = resolver, parsed.hostname, port

    def _validate_live_endpoint(self) -> None:
        """Re-resolve immediately before every request to reject DNS rebinding."""
        client_endpoint = str(getattr(getattr(self.client, 'meta', None), 'endpoint_url', ''))
        if client_endpoint.rstrip('/') != self.endpoint:
            raise ObjectStorageError('object:client_endpoint_mismatch')
        try:
            addresses = {item[4][0] for item in self._resolver(self._hostname, self._port)}
            if not addresses or any(
                not ipaddress.ip_address(value).is_global for value in addresses
            ):
                raise ObjectStorageError('object:configuration_invalid')
        except (OSError, TypeError, ValueError) as exc:
            raise ObjectStorageError('object:configuration_invalid') from exc

    @staticmethod
    def _key(*, tenant_id: str, namespace: str, object_id: str) -> str:
        candidate = f'{tenant_id}/{namespace}/{object_id}'
        if not OBJECT.fullmatch(candidate) or '..' in candidate.split('/'):
            raise ObjectStorageError('object:key_invalid')
        return candidate

    def put(
        self, *, tenant_id: str, namespace: str, object_id: str, content: bytes
    ) -> ObjectReceipt:
        if not isinstance(content, bytes) or not 1 <= len(content) <= 100 * 1024 * 1024:
            raise ObjectStorageError('object:size_invalid')
        key = self._key(tenant_id=tenant_id, namespace=namespace, object_id=object_id)
        self._validate_live_endpoint()
        digest = hashlib.sha256(content).hexdigest()
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType='application/octet-stream',
            Metadata={'sha256': digest},
            ServerSideEncryption='AES256',
            CacheControl='private,no-store',
        )
        return ObjectReceipt(tenant_id, self.bucket, key, digest, len(content))

    def get(self, *, tenant_id: str, receipt: ObjectReceipt) -> bytes:
        if (
            receipt.tenant_id != tenant_id
            or receipt.bucket != self.bucket
            or not OBJECT.fullmatch(receipt.key)
            or not receipt.key.startswith(f'{tenant_id}/')
        ):
            raise ObjectStorageError('object:ownership_invalid')
        self._validate_live_endpoint()
        response = self.client.get_object(Bucket=self.bucket, Key=receipt.key)
        content = response['Body'].read()
        if (
            len(content) != receipt.byte_size
            or hashlib.sha256(content).hexdigest() != receipt.sha256
        ):
            raise ObjectStorageError('object:integrity_invalid')
        return content

    def delete(self, *, tenant_id: str, receipt: ObjectReceipt) -> None:
        self.get(tenant_id=tenant_id, receipt=receipt)
        self._validate_live_endpoint()
        self.client.delete_object(Bucket=self.bucket, Key=receipt.key)
