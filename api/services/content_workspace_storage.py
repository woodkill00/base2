from __future__ import annotations

import hashlib
import os
import re
import tempfile
import base64
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


SAFE_SEGMENT = re.compile(r'^[a-z0-9][a-z0-9_-]{0,62}$')
SAFE_OBJECT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
SHA256 = re.compile(r'^[a-f0-9]{64}$')
FORMAT_VERSION = b'CW1'


class ArtifactIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class StoredArtifact:
    object_key: str
    sha256: str
    byte_size: int


class PrivateArtifactStore:
    """Small encrypted exact-owned store for private workspace artifacts.

    Object names are server-derived closed segments. Payloads are encrypted with
    authenticated context bound to the complete object key and created without
    overwrite, making retries idempotent and conflicting reuse fail closed.
    """

    def __init__(self, root: str | Path, *, key: bytes, max_bytes: int = 10 * 1024 * 1024):
        supplied = Path(root)
        if supplied.is_symlink():
            raise ArtifactIntegrityError('content_artifact_root_invalid')
        if not isinstance(key, bytes) or len(key) != 32:
            raise ArtifactIntegrityError('content_artifact_key_invalid')
        if not 1 <= max_bytes <= 100 * 1024 * 1024:
            raise ArtifactIntegrityError('content_limit_exceeded')
        supplied.mkdir(mode=0o700, parents=True, exist_ok=True)
        supplied.chmod(0o700)
        self._root = supplied.resolve(strict=True)
        self._key = key
        self._max_bytes = max_bytes

    @staticmethod
    def object_key(*, namespace: str, site_id: str, object_id: str) -> str:
        if (
            not SAFE_SEGMENT.fullmatch(namespace or '')
            or not SAFE_SEGMENT.fullmatch(site_id or '')
            or not SAFE_OBJECT.fullmatch(object_id or '')
        ):
            raise ArtifactIntegrityError('content_artifact_key_invalid')
        return f'{namespace}/{site_id}/{object_id}.bin'

    def _path(self, object_key: str) -> Path:
        parts = object_key.split('/')
        if (
            len(parts) != 3
            or not SAFE_SEGMENT.fullmatch(parts[0])
            or not SAFE_SEGMENT.fullmatch(parts[1])
            or not parts[2].endswith('.bin')
            or not SAFE_OBJECT.fullmatch(parts[2][:-4])
        ):
            raise ArtifactIntegrityError('content_artifact_key_invalid')
        path = self._root.joinpath(*parts)
        if self._root not in path.parents:
            raise ArtifactIntegrityError('content_artifact_key_invalid')
        return path

    def put(
        self, *, namespace: str, site_id: str, object_id: str, content: bytes
    ) -> StoredArtifact:
        if not isinstance(content, bytes) or not content or len(content) > self._max_bytes:
            raise ArtifactIntegrityError('content_limit_exceeded')
        object_key = self.object_key(
            namespace=namespace,
            site_id=site_id,
            object_id=object_id,
        )
        path = self._path(object_key)
        digest = hashlib.sha256(content).hexdigest()
        result = StoredArtifact(object_key=object_key, sha256=digest, byte_size=len(content))
        if path.exists():
            if self._read_decrypted(object_key) == content:
                return result
            raise ArtifactIntegrityError('content_artifact_conflict')

        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.parent.chmod(0o700)
        nonce = os.urandom(12)
        encrypted = AESGCM(self._key).encrypt(nonce, content, object_key.encode())
        envelope = FORMAT_VERSION + nonce + encrypted
        temporary: str | None = None
        try:
            descriptor, temporary = tempfile.mkstemp(prefix='.workspace-', dir=path.parent)
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if self._read_decrypted(object_key) != content:
                    raise ArtifactIntegrityError('content_artifact_conflict') from None
            return result
        finally:
            if temporary:
                with suppress(FileNotFoundError):
                    os.unlink(temporary)

    def get(self, object_key: str, *, expected_sha256: str) -> bytes:
        if not SHA256.fullmatch(expected_sha256 or ''):
            raise ArtifactIntegrityError('content_integrity_failed')
        content = self._read_decrypted(object_key)
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            raise ArtifactIntegrityError('content_integrity_failed')
        return content

    def _read_decrypted(self, object_key: str) -> bytes:
        path = self._path(object_key)
        try:
            envelope = path.read_bytes()
        except (FileNotFoundError, OSError) as exc:
            raise ArtifactIntegrityError('content_artifact_unavailable') from exc
        if len(envelope) < len(FORMAT_VERSION) + 12 + 16 or not envelope.startswith(
            FORMAT_VERSION
        ):
            raise ArtifactIntegrityError('content_integrity_failed')
        nonce = envelope[len(FORMAT_VERSION) : len(FORMAT_VERSION) + 12]
        ciphertext = envelope[len(FORMAT_VERSION) + 12 :]
        try:
            content = AESGCM(self._key).decrypt(nonce, ciphertext, object_key.encode())
        except (InvalidTag, ValueError) as exc:
            raise ArtifactIntegrityError('content_integrity_failed') from exc
        if len(content) > self._max_bytes:
            raise ArtifactIntegrityError('content_integrity_failed')
        return content


def configured_artifact_store(*, root: str, encoded_key: str) -> PrivateArtifactStore:
    """Build the store from explicit settings without accepting ambient paths or weak keys."""
    if not isinstance(root, str) or not root.startswith('/') or not encoded_key:
        raise ArtifactIntegrityError('content_artifact_configuration_invalid')
    try:
        padded = encoded_key + '=' * (-len(encoded_key) % 4)
        key = base64.urlsafe_b64decode(padded.encode())
    except (ValueError, TypeError) as exc:
        raise ArtifactIntegrityError('content_artifact_configuration_invalid') from exc
    if len(key) != 32:
        raise ArtifactIntegrityError('content_artifact_configuration_invalid')
    return PrivateArtifactStore(root, key=key)
