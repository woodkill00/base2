from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from pathlib import PurePath


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MEDIA_LIBRARY_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_IMAGE_EDGE = 12_000
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_MEDIA = {
    'image/jpeg': (b'\xff\xd8\xff',),
    'image/png': (b'\x89PNG\r\n\x1a\n',),
    'image/webp': (b'RIFF',),
    'application/pdf': (b'%PDF-',),
    'audio/mpeg': (b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'),
    'audio/ogg': (b'OggS',),
    'video/mp4': (),
    'video/webm': (b'\x1aE\xdf\xa3',),
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
    width: int | None = None
    height: int | None = None
    state: str = 'quarantined'


def _image_dimensions(content: bytes, media_type: str) -> tuple[int, int] | tuple[None, None]:
    if media_type in {'application/pdf', 'audio/mpeg', 'audio/ogg', 'video/mp4', 'video/webm'}:
        return None, None
    if media_type == 'image/png':
        if len(content) < 33 or content[12:16] != b'IHDR':
            raise MediaAdmissionError('content_media_signature_invalid')
        return int.from_bytes(content[16:20], 'big'), int.from_bytes(content[20:24], 'big')
    if media_type == 'image/webp':
        if len(content) < 30:
            raise MediaAdmissionError('content_media_signature_invalid')
        kind = content[12:16]
        if kind == b'VP8X':
            return (
                1 + int.from_bytes(content[24:27], 'little'),
                1 + int.from_bytes(content[27:30], 'little'),
            )
        raise MediaAdmissionError('content_media_signature_invalid')
    if media_type == 'image/jpeg':
        position = 2
        while position + 4 <= len(content):
            if content[position] != 0xFF:
                raise MediaAdmissionError('content_media_signature_invalid')
            marker = content[position + 1]
            position += 2
            if marker in {0xD8, 0xD9}:
                continue
            if position + 2 > len(content):
                break
            length = int.from_bytes(content[position : position + 2], 'big')
            if length < 2 or position + length > len(content):
                break
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB}:
                if length < 7:
                    break
                return (
                    int.from_bytes(content[position + 5 : position + 7], 'big'),
                    int.from_bytes(content[position + 3 : position + 5], 'big'),
                )
            position += length
        raise MediaAdmissionError('content_media_signature_invalid')
    raise MediaAdmissionError('content_media_type_invalid')


def _validate_dimensions(width: int | None, height: int | None) -> None:
    if width is None and height is None:
        return
    if (
        not width
        or not height
        or width > MAX_IMAGE_EDGE
        or height > MAX_IMAGE_EDGE
        or width * height > MAX_IMAGE_PIXELS
    ):
        raise MediaAdmissionError('content_media_dimensions_invalid')


def admit_upload(
    *, filename: str, claimed_type: str, content: bytes, maximum_bytes: int = MAX_UPLOAD_BYTES
) -> MediaAdmission:
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
    if (
        not isinstance(maximum_bytes, int)
        or isinstance(maximum_bytes, bool)
        or not 1 <= maximum_bytes <= MEDIA_LIBRARY_MAX_UPLOAD_BYTES
        or not isinstance(content, bytes)
        or not content
        or len(content) > maximum_bytes
    ):
        raise MediaAdmissionError('content_limit_exceeded')
    signatures = ALLOWED_MEDIA[claimed_type]
    if signatures and not any(content.startswith(signature) for signature in signatures):
        raise MediaAdmissionError('content_media_signature_invalid')
    if claimed_type == 'video/mp4' and (
        len(content) < 12 or content[4:8] != b'ftyp' or content[8:12] in {b'qt  ', b'M4A '}
    ):
        raise MediaAdmissionError('content_media_signature_invalid')
    if claimed_type == 'image/webp' and content[8:12] != b'WEBP':
        raise MediaAdmissionError('content_media_signature_invalid')
    lowered = content.lower()
    if any(
        marker in lowered
        for marker in (b'<script', b'<html', b'javascript:', b'<?php', b'mz\x90', b'#!/bin/')
    ):
        raise MediaAdmissionError('content_media_active_content')
    width, height = _image_dimensions(content, claimed_type)
    _validate_dimensions(width, height)
    return MediaAdmission(
        safe_name=filename,
        media_type=claimed_type,
        byte_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        width=width,
        height=height,
    )


def apply_scan_result(
    admission: MediaAdmission, *, outcome: str, scanned_sha256: str
) -> MediaAdmission:
    """Apply a scanner verdict without allowing a different object to be promoted."""
    if outcome not in {'clean', 'infected', 'error'}:
        raise MediaAdmissionError('content_media_scan_invalid')
    if scanned_sha256 != admission.sha256:
        raise MediaAdmissionError('content_integrity_failed')
    # A scanner only answers whether the exact upload contains a known threat.
    # Validation additionally requires a separately generated safe derivative.
    state = {'clean': 'quarantined', 'infected': 'rejected', 'error': 'quarantined'}[outcome]
    return replace(admission, state=state)
