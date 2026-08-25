from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

_KEY = re.compile(r'^[A-Za-z][A-Za-z0-9_.-]{0,63}$')
_CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_HOSTILE_MARKUP = re.compile(r'<\s*(script|iframe|object|embed)\b|javascript\s*:', re.I)


class FormPolicyError(ValueError):
    pass


class MediaPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class MediaInspection:
    original_name: str
    sniffed_type: str
    byte_size: int
    sha256: str
    attribution: str
    status: str
    metadata: dict[str, str]


def _normalize(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        raise FormPolicyError('payload_too_deep')
    if isinstance(value, dict):
        if len(value) > 50:
            raise FormPolicyError('payload_too_many_fields')
        normalized = {}
        for key in sorted(value):
            if not isinstance(key, str) or not _KEY.fullmatch(key):
                raise FormPolicyError('payload_key_invalid')
            normalized[key] = _normalize(value[key], depth=depth + 1)
        return normalized
    if isinstance(value, list):
        if len(value) > 50:
            raise FormPolicyError('payload_too_many_items')
        return [_normalize(item, depth=depth + 1) for item in value]
    if isinstance(value, str):
        value = value.strip()
        if len(value) > 10_000:
            raise FormPolicyError('payload_value_too_large')
        if _CONTROL.search(value):
            raise FormPolicyError('payload_control_character')
        if _HOSTILE_MARKUP.search(value):
            raise FormPolicyError('payload_markup_forbidden')
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise FormPolicyError('payload_type_invalid')


def validate_form_submission(payload: dict[str, Any], consent: dict[str, Any]):
    if not isinstance(payload, dict) or not isinstance(consent, dict):
        raise FormPolicyError('payload_type_invalid')
    if payload.get('_gotcha'):
        raise FormPolicyError('spam_rejected')
    payload = {key: value for key, value in payload.items() if key != '_gotcha'}
    normalized_payload = _normalize(payload)
    normalized_consent = _normalize(consent)
    try:
        encoded_payload = json.dumps(
            normalized_payload, sort_keys=True, separators=(',', ':'), allow_nan=False
        ).encode()
        encoded_consent = json.dumps(
            normalized_consent, sort_keys=True, separators=(',', ':'), allow_nan=False
        ).encode()
    except (TypeError, ValueError) as exc:
        raise FormPolicyError('payload_type_invalid') from exc
    if len(encoded_payload) > 32_768:
        raise FormPolicyError('payload_too_large')
    if len(encoded_consent) > 4_096:
        raise FormPolicyError('consent_too_large')
    return normalized_payload, normalized_consent


def _sniff_media(content: bytes) -> str | None:
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if content.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if len(content) >= 12 and content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'image/webp'
    if content.startswith(b'%PDF-'):
        return 'application/pdf'
    return None


def inspect_media_upload(
    content: bytes,
    *,
    original_name: str,
    claimed_type: str,
    allowed_types: set[str],
    max_bytes: int,
    attribution: str = '',
) -> MediaInspection:
    if not isinstance(content, bytes) or not content:
        raise MediaPolicyError('media_empty')
    if len(content) > max_bytes:
        raise MediaPolicyError('media_too_large')
    if (
        not original_name
        or len(original_name) > 255
        or PurePath(original_name).name != original_name
        or _CONTROL.search(original_name)
    ):
        raise MediaPolicyError('filename_invalid')
    sniffed = _sniff_media(content)
    if sniffed is None or sniffed not in allowed_types:
        raise MediaPolicyError('media_type_forbidden')
    if claimed_type.strip().lower() != sniffed:
        raise MediaPolicyError('mime_mismatch')
    attribution = attribution.strip()
    if len(attribution) > 2_000:
        raise MediaPolicyError('attribution_too_large')
    if _CONTROL.search(attribution) or _HOSTILE_MARKUP.search(attribution):
        raise MediaPolicyError('attribution_invalid')
    return MediaInspection(
        original_name=original_name,
        sniffed_type=sniffed,
        byte_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        attribution=attribution,
        status='quarantined',
        metadata={'metadataPolicy': 'stripped'},
    )
