from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePath


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MEDIA = {
    'image/jpeg': (b'\xff\xd8\xff',),
    'image/png': (b'\x89PNG\r\n\x1a\n',),
    'image/webp': (b'RIFF',),
    'application/pdf': (b'%PDF-',),
}
SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._ -]{0,199}$')


class MediaAdmissionError(ValueError):
    pass


@dataclass(frozen=True)
class MediaAdmission:
    safe_name: str
    media_type: str
    byte_size: int
    sha256: str
    state: str = 'quarantined'


def admit_upload(*, filename: str, claimed_type: str, content: bytes) -> MediaAdmission:
    if (
        not isinstance(filename, str)
        or not SAFE_NAME.fullmatch(filename)
        or PurePath(filename).name != filename
        or '/' in filename
        or '\\' in filename
    ):
        raise MediaAdmissionError('content_media_filename_invalid')
    if claimed_type not in ALLOWED_MEDIA:
        raise MediaAdmissionError('content_media_type_invalid')
    if not isinstance(content, bytes) or not content or len(content) > MAX_UPLOAD_BYTES:
        raise MediaAdmissionError('content_limit_exceeded')
    if not any(content.startswith(signature) for signature in ALLOWED_MEDIA[claimed_type]):
        raise MediaAdmissionError('content_media_signature_invalid')
    if claimed_type == 'image/webp' and content[8:12] != b'WEBP':
        raise MediaAdmissionError('content_media_signature_invalid')
    lower_head = content[:4096].lower()
    if any(marker in lower_head for marker in (b'<script', b'javascript:', b'<?php', b'mz\x90')):
        raise MediaAdmissionError('content_media_active_content')
    return MediaAdmission(
        safe_name=filename,
        media_type=claimed_type,
        byte_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )
