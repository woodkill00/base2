"""Closed, provider-neutral policy primitives for the Base2 media library.

This module deliberately has no network, filesystem, database, or credential
access.  It is safe to use from API validation, workers, generators, and tests.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


MEBIBYTE = 1024 * 1024
SHA256 = re.compile(r"^[a-f0-9]{64}$")
SAFE_CODE = re.compile(r"^media_[a-z0-9_]{3,63}$")
CONTROL_OR_BIDI = re.compile(r"[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]")
SAFE_DISPLAY_NAME = re.compile(r"^[^/\\]{1,200}$")
RESERVED_STEMS = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


class MediaPolicyError(ValueError):
    pass


class DeliveryMode(StrEnum):
    SAFE_INLINE = "safe_inline"
    FORCED_DOWNLOAD = "forced_download"
    PREVIEW_ONLY = "preview_only"
    REJECT = "reject"


@dataclass(frozen=True)
class FormatRule:
    media_type: str
    extensions: tuple[str, ...]
    maximum_bytes: int
    delivery: DeliveryMode
    decoder: str
    derivative_recipe: str | None


FORMAT_RULES: dict[str, FormatRule] = {
    "image/jpeg": FormatRule(
        "image/jpeg", ("jpg", "jpeg"), 25 * MEBIBYTE,
        DeliveryMode.PREVIEW_ONLY, "pillow", "safe-raster-v1",
    ),
    "image/png": FormatRule(
        "image/png", ("png",), 25 * MEBIBYTE,
        DeliveryMode.PREVIEW_ONLY, "pillow", "safe-raster-v1",
    ),
    "image/webp": FormatRule(
        "image/webp", ("webp",), 25 * MEBIBYTE,
        DeliveryMode.PREVIEW_ONLY, "pillow", "safe-raster-v1",
    ),
    "application/pdf": FormatRule(
        "application/pdf", ("pdf",), 25 * MEBIBYTE,
        DeliveryMode.FORCED_DOWNLOAD, "pypdf", "safe-pdf-preview-v1",
    ),
    "audio/mpeg": FormatRule(
        "audio/mpeg", ("mp3",), 50 * MEBIBYTE,
        DeliveryMode.FORCED_DOWNLOAD, "ffprobe", "safe-audio-preview-v1",
    ),
    "audio/ogg": FormatRule(
        "audio/ogg", ("ogg", "oga"), 50 * MEBIBYTE,
        DeliveryMode.FORCED_DOWNLOAD, "ffprobe", "safe-audio-preview-v1",
    ),
    "video/mp4": FormatRule(
        "video/mp4", ("mp4",), 100 * MEBIBYTE,
        DeliveryMode.FORCED_DOWNLOAD, "ffprobe", "safe-video-preview-v1",
    ),
    "video/webm": FormatRule(
        "video/webm", ("webm",), 100 * MEBIBYTE,
        DeliveryMode.FORCED_DOWNLOAD, "ffprobe", "safe-video-preview-v1",
    ),
}


DEFAULT_POLICY = {
    "schemaVersion": 1,
    "enabled": False,
    "allowedTypes": ["image/jpeg", "image/png", "image/webp", "application/pdf"],
    "maximumObjectBytes": 25 * MEBIBYTE,
    "maximumBatchFiles": 20,
    "maximumBatchBytes": 100 * MEBIBYTE,
    "maximumConcurrentProcessing": 4,
    "uploadSessionMinutes": 30,
    "deliveryGrantMinutes": 5,
    "scannerMaximumAgeHours": 24,
    "storageAdapter": "local-private",
    "scannerAdapter": "clamav",
}
POLICY_KEYS = frozenset(DEFAULT_POLICY)


def validate_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != POLICY_KEYS:
        raise MediaPolicyError("media_policy_fields_invalid")
    if value.get("schemaVersion") != 1 or not isinstance(value.get("enabled"), bool):
        raise MediaPolicyError("media_policy_version_invalid")
    types = value.get("allowedTypes")
    if (
        not isinstance(types, list)
        or not types
        or len(types) != len(set(types))
        or any(item not in FORMAT_RULES for item in types)
    ):
        raise MediaPolicyError("media_policy_types_invalid")
    integer_bounds = {
        "maximumObjectBytes": (1, 100 * MEBIBYTE),
        "maximumBatchFiles": (1, 100),
        "maximumBatchBytes": (1, 500 * MEBIBYTE),
        "maximumConcurrentProcessing": (1, 16),
        "uploadSessionMinutes": (5, 120),
        "deliveryGrantMinutes": (1, 15),
        "scannerMaximumAgeHours": (1, 72),
    }
    for field, (minimum, maximum) in integer_bounds.items():
        candidate = value.get(field)
        if not isinstance(candidate, int) or isinstance(candidate, bool) or not minimum <= candidate <= maximum:
            raise MediaPolicyError("media_policy_limit_invalid")
    if value["maximumBatchBytes"] < value["maximumObjectBytes"]:
        raise MediaPolicyError("media_policy_batch_invalid")
    if value.get("storageAdapter") not in {"local-private", "s3-compatible"}:
        raise MediaPolicyError("media_policy_storage_invalid")
    if value.get("scannerAdapter") != "clamav":
        raise MediaPolicyError("media_policy_scanner_invalid")
    return {
        key: list(item) if isinstance(item := value[key], list) else item
        for key in sorted(POLICY_KEYS)
    }


def normalize_display_name(value: Any) -> str:
    if not isinstance(value, str):
        raise MediaPolicyError("media_filename_invalid")
    normalized = unicodedata.normalize("NFC", value)
    if (
        normalized != value
        or value != value.strip()
        or not SAFE_DISPLAY_NAME.fullmatch(value)
        or CONTROL_OR_BIDI.search(value)
        or value.endswith((".", " "))
    ):
        raise MediaPolicyError("media_filename_invalid")
    stem = value.rsplit(".", 1)[0].casefold()
    if stem in RESERVED_STEMS or ".." in value:
        raise MediaPolicyError("media_filename_invalid")
    return value


def rule_for(*, display_name: str, claimed_type: Any) -> FormatRule:
    safe_name = normalize_display_name(display_name)
    if not isinstance(claimed_type, str) or claimed_type not in FORMAT_RULES:
        raise MediaPolicyError("media_type_invalid")
    suffix = safe_name.rsplit(".", 1)[-1].casefold() if "." in safe_name else ""
    rule = FORMAT_RULES[claimed_type]
    if suffix not in rule.extensions:
        raise MediaPolicyError("media_extension_type_mismatch")
    return rule


def validate_digest(value: Any) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise MediaPolicyError("media_digest_invalid")
    return value


def scanner_is_ready(
    *,
    engine: Any,
    definitions_updated_at: Any,
    observed_at: Any,
    maximum_age_hours: int,
) -> bool:
    if engine != "clamav" or not isinstance(definitions_updated_at, datetime) or not isinstance(observed_at, datetime):
        return False
    if definitions_updated_at.tzinfo is None or observed_at.tzinfo is None:
        return False
    updated = definitions_updated_at.astimezone(UTC)
    observed = observed_at.astimezone(UTC)
    return (
        1 <= maximum_age_hours <= 72
        and updated <= observed
        and observed - updated <= timedelta(hours=maximum_age_hours)
    )


def safe_error_code(value: Any) -> str:
    return value if isinstance(value, str) and SAFE_CODE.fullmatch(value) else "media_dependency_unavailable"


def delivery_headers(*, media_type: str, inline_safe_derivative: bool) -> dict[str, str]:
    if media_type not in FORMAT_RULES:
        raise MediaPolicyError("media_type_invalid")
    disposition = "inline" if inline_safe_derivative and media_type in {"image/jpeg", "image/png", "image/webp"} else "attachment"
    return {
        "Cache-Control": "private, no-store",
        "Content-Disposition": disposition,
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Content-Type": media_type,
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }
