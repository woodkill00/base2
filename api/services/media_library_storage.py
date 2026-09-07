"""Provider-neutral, exact-owned storage contracts for the media library."""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from api.services.media_library_policy import validate_digest


OBJECT_KEY = re.compile(
    r'^media/(?P<site>[a-z][a-z0-9-]{2,62})/(?P<object>[a-f0-9]{32})/'
    r'v(?P<version>[1-9][0-9]{0,9})/(?P<digest>[a-f0-9]{64})\.bin$'
)
PART_KEY = re.compile(
    r'^media-parts/(?P<site>[a-z][a-z0-9-]{2,62})/(?P<session>[a-f0-9]{32})/'
    r'p(?P<part>[1-9][0-9]{0,4})/(?P<digest>[a-f0-9]{64})\.bin$'
)
SECRET_REF = re.compile(r'^secretref:[a-z][a-z0-9/_-]{2,127}$')


class MediaStorageError(ValueError):
    pass


@dataclass(frozen=True)
class ObjectHead:
    key: str
    sha256: str
    byte_size: int
    transport_etag: str


@dataclass(frozen=True)
class SignedDelivery:
    url: str
    expires_at: datetime
    method: str
    key: str
    sha256: str
    byte_size: int
    audience_ref: str


class MediaObjectStorage(Protocol):
    def put_part(self, *, key: str, content: bytes) -> ObjectHead: ...
    def complete(self, *, key: str, parts: tuple[str, ...], expected_sha256: str) -> ObjectHead: ...
    def read(self, *, key: str, expected_sha256: str) -> bytes: ...
    def head(self, *, key: str) -> ObjectHead: ...
    def copy(self, *, source_key: str, target_key: str, expected_sha256: str) -> ObjectHead: ...
    def delete(self, *, key: str, expected_sha256: str, missing_ok: bool = False) -> bool: ...
    def sign(
        self,
        *,
        key: str,
        expected_sha256: str,
        method: str,
        audience_ref: str,
        observed_at: datetime,
        lifetime: timedelta,
    ) -> SignedDelivery: ...
    def list_owned(self, *, prefix: str) -> tuple[ObjectHead, ...]: ...
    def reconcile(self, *, prefix: str, expected_keys: frozenset[str]) -> tuple[str, ...]: ...


def _validated_key(key: str, *, allow_part: bool = True) -> re.Match[str]:
    match = OBJECT_KEY.fullmatch(key or '')
    if match is None and allow_part:
        match = PART_KEY.fullmatch(key or '')
    if match is None or not hmac.compare_digest(match.group('digest'), key.rsplit('/', 1)[-1][:-4]):
        raise MediaStorageError('media_storage_key_invalid')
    return match


def _digest(content: bytes) -> str:
    if not isinstance(content, bytes) or not content:
        raise MediaStorageError('media_storage_content_invalid')
    return hashlib.sha256(content).hexdigest()


class InMemoryMediaObjectStorage:
    """Deterministic non-production adapter with immutable, digest-bound objects."""

    def __init__(self, *, signing_origin: str = 'https://media.invalid') -> None:
        self._objects: dict[str, bytes] = {}
        self._origin = signing_origin.rstrip('/')

    @staticmethod
    def _head(key: str, content: bytes) -> ObjectHead:
        digest = hashlib.sha256(content).hexdigest()
        return ObjectHead(key, digest, len(content), f'"transport-{digest[:16]}"')

    def put_part(self, *, key: str, content: bytes) -> ObjectHead:
        match = _validated_key(key)
        digest = _digest(content)
        if not hmac.compare_digest(match.group('digest'), digest):
            raise MediaStorageError('media_storage_digest_mismatch')
        current = self._objects.get(key)
        if current is not None and current != content:
            raise MediaStorageError('media_storage_immutable_conflict')
        self._objects[key] = content
        return self._head(key, content)

    def complete(self, *, key: str, parts: tuple[str, ...], expected_sha256: str) -> ObjectHead:
        match = _validated_key(key, allow_part=False)
        validate_digest(expected_sha256)
        if match.group('digest') != expected_sha256 or not parts or len(parts) > 10_000:
            raise MediaStorageError('media_storage_complete_invalid')
        site = match.group('site')
        if len(set(parts)) != len(parts):
            raise MediaStorageError('media_storage_complete_invalid')
        try:
            content = b''.join(self._objects[part] for part in parts)
        except KeyError as exc:
            raise MediaStorageError('media_storage_part_missing') from exc
        for part in parts:
            part_match = _validated_key(part)
            if not part.startswith('media-parts/') or part_match.group('site') != site:
                raise MediaStorageError('media_storage_owner_mismatch')
        if _digest(content) != expected_sha256:
            raise MediaStorageError('media_storage_digest_mismatch')
        current = self._objects.get(key)
        if current is not None and current != content:
            raise MediaStorageError('media_storage_immutable_conflict')
        self._objects[key] = content
        return self._head(key, content)

    def read(self, *, key: str, expected_sha256: str) -> bytes:
        _validated_key(key)
        validate_digest(expected_sha256)
        try:
            content = self._objects[key]
        except KeyError as exc:
            raise MediaStorageError('media_storage_not_found') from exc
        if not hmac.compare_digest(hashlib.sha256(content).hexdigest(), expected_sha256):
            raise MediaStorageError('media_storage_integrity_failed')
        return content

    def head(self, *, key: str) -> ObjectHead:
        _validated_key(key)
        try:
            return self._head(key, self._objects[key])
        except KeyError as exc:
            raise MediaStorageError('media_storage_not_found') from exc

    def copy(self, *, source_key: str, target_key: str, expected_sha256: str) -> ObjectHead:
        source = self.read(key=source_key, expected_sha256=expected_sha256)
        target = _validated_key(target_key, allow_part=False)
        if target.group('digest') != expected_sha256:
            raise MediaStorageError('media_storage_digest_mismatch')
        return self.put_part(key=target_key, content=source)

    def delete(self, *, key: str, expected_sha256: str, missing_ok: bool = False) -> bool:
        _validated_key(key)
        if key not in self._objects:
            if missing_ok:
                return False
            raise MediaStorageError('media_storage_not_found')
        self.read(key=key, expected_sha256=expected_sha256)
        del self._objects[key]
        return True

    def sign(
        self,
        *,
        key: str,
        expected_sha256: str,
        method: str,
        audience_ref: str,
        observed_at: datetime,
        lifetime: timedelta,
    ) -> SignedDelivery:
        self.read(key=key, expected_sha256=expected_sha256)
        if (
            method not in {'GET', 'HEAD'}
            or observed_at.tzinfo is None
            or not timedelta(seconds=1) <= lifetime <= timedelta(minutes=15)
            or not re.fullmatch(r'[a-z][a-z0-9:._-]{2,199}', audience_ref or '')
        ):
            raise MediaStorageError('media_storage_grant_invalid')
        expiry = observed_at.astimezone(UTC) + lifetime
        # The fake emits a non-secret opaque marker, never an object key.
        marker = hashlib.sha256(
            f'{method}\0{key}\0{audience_ref}\0{expiry.isoformat()}'.encode()
        ).hexdigest()
        return SignedDelivery(
            f'{self._origin}/delivery/{marker}',
            expiry,
            method,
            key,
            expected_sha256,
            len(self._objects[key]),
            audience_ref,
        )

    def list_owned(self, *, prefix: str) -> tuple[ObjectHead, ...]:
        if not re.fullmatch(r'media(?:-parts)?/[a-z][a-z0-9-]{2,62}/', prefix or ''):
            raise MediaStorageError('media_storage_prefix_invalid')
        return tuple(
            self._head(key, self._objects[key])
            for key in sorted(self._objects)
            if key.startswith(prefix)
        )

    def reconcile(self, *, prefix: str, expected_keys: frozenset[str]) -> tuple[str, ...]:
        observed = self.list_owned(prefix=prefix)
        for key in expected_keys:
            if not key.startswith(prefix):
                raise MediaStorageError('media_storage_owner_mismatch')
            _validated_key(key)
        return tuple(item.key for item in observed if item.key not in expected_keys)


class RuntimeMediaObjectStorage:
    """Production adapter boundary; credentials are resolved by the runtime only."""

    def __init__(self, *, client, credential_ref: str, bucket: str) -> None:
        if not SECRET_REF.fullmatch(credential_ref or ''):
            raise MediaStorageError('media_storage_secretref_invalid')
        if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{2,62}', bucket or ''):
            raise MediaStorageError('media_storage_bucket_invalid')
        required = {'put_part', 'complete', 'read', 'head', 'copy', 'delete', 'sign', 'list_owned'}
        if any(not callable(getattr(client, name, None)) for name in required):
            raise MediaStorageError('media_storage_client_invalid')
        self._client = client
        self._bucket = bucket

    def __getattr__(self, name: str):
        if name.startswith('_'):
            raise AttributeError(name)
        return getattr(self._client, name)

    def reconcile(self, *, prefix: str, expected_keys: frozenset[str]) -> tuple[str, ...]:
        observed = self._client.list_owned(bucket=self._bucket, prefix=prefix)
        return tuple(sorted(item.key for item in observed if item.key not in expected_keys))
