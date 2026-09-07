from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from api.services.media_library_policy import (
    DEFAULT_POLICY,
    FORMAT_RULES,
    DeliveryMode,
    MediaPolicyError,
    delivery_headers,
    normalize_display_name,
    rule_for,
    safe_error_code,
    scanner_is_ready,
    validate_digest,
    validate_policy,
)


def policy(**changes):
    value = deepcopy(DEFAULT_POLICY)
    value.update(changes)
    return value


def test_default_policy_is_closed_disabled_and_deterministic():
    first = validate_policy(policy())
    second = validate_policy(policy())
    assert first == second
    assert first["enabled"] is False
    assert first["allowedTypes"] == ["image/jpeg", "image/png", "image/webp", "application/pdf"]


@pytest.mark.parametrize(
    "change,code",
    [
        ({"extra": True}, "media_policy_fields_invalid"),
        ({"schemaVersion": 2}, "media_policy_version_invalid"),
        ({"enabled": 1}, "media_policy_version_invalid"),
        ({"allowedTypes": []}, "media_policy_types_invalid"),
        ({"allowedTypes": ["image/svg+xml"]}, "media_policy_types_invalid"),
        ({"allowedTypes": ["image/png", "image/png"]}, "media_policy_types_invalid"),
        ({"maximumObjectBytes": True}, "media_policy_limit_invalid"),
        ({"maximumObjectBytes": 0}, "media_policy_limit_invalid"),
        ({"maximumBatchFiles": 101}, "media_policy_limit_invalid"),
        ({"deliveryGrantMinutes": 16}, "media_policy_limit_invalid"),
        ({"storageAdapter": "arbitrary"}, "media_policy_storage_invalid"),
        ({"scannerAdapter": "none"}, "media_policy_scanner_invalid"),
    ],
)
def test_policy_rejects_unknown_unsafe_and_out_of_bound_values(change, code):
    with pytest.raises(MediaPolicyError, match=code):
        validate_policy(policy(**change))


def test_batch_must_hold_at_least_one_maximum_object():
    with pytest.raises(MediaPolicyError, match="media_policy_batch_invalid"):
        validate_policy(policy(maximumObjectBytes=20, maximumBatchBytes=10))


@pytest.mark.parametrize("name", ["photo.jpg", "résumé final.pdf", "clip-01.webm"])
def test_display_names_are_metadata_not_paths(name):
    assert normalize_display_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "../escape.png", "folder/file.png", "folder\\file.png", " image.png",
        "image.png ", "image.png.", "CON.png", "a..png", "bad\u202eexe.png",
        "decomposed-e\u0301.png", "x\x00.png", "",
    ],
)
def test_unsafe_ambiguous_or_noncanonical_names_fail(name):
    with pytest.raises(MediaPolicyError, match="media_filename_invalid"):
        normalize_display_name(name)


def test_declared_type_and_extension_must_agree():
    assert rule_for(display_name="safe.jpeg", claimed_type="image/jpeg").decoder == "pillow"
    with pytest.raises(MediaPolicyError, match="media_extension_type_mismatch"):
        rule_for(display_name="safe.png", claimed_type="image/jpeg")
    with pytest.raises(MediaPolicyError, match="media_type_invalid"):
        rule_for(display_name="safe.svg", claimed_type="image/svg+xml")


def test_format_matrix_does_not_inline_unreviewed_originals():
    assert FORMAT_RULES
    assert all(rule.delivery is not DeliveryMode.SAFE_INLINE for rule in FORMAT_RULES.values())
    assert FORMAT_RULES["application/pdf"].delivery is DeliveryMode.FORCED_DOWNLOAD


def test_digest_contract_accepts_only_canonical_sha256():
    assert validate_digest("a" * 64) == "a" * 64
    for value in ("A" * 64, "a" * 63, "not-a-digest", None):
        with pytest.raises(MediaPolicyError, match="media_digest_invalid"):
            validate_digest(value)


def test_scanner_freshness_is_timezone_aware_bounded_and_never_future():
    now = datetime(2026, 9, 6, tzinfo=UTC)
    assert scanner_is_ready(
        engine="clamav", definitions_updated_at=now - timedelta(hours=1),
        observed_at=now, maximum_age_hours=24,
    )
    assert not scanner_is_ready(
        engine="clamav", definitions_updated_at=now - timedelta(hours=25),
        observed_at=now, maximum_age_hours=24,
    )
    assert not scanner_is_ready(
        engine="clamav", definitions_updated_at=now + timedelta(seconds=1),
        observed_at=now, maximum_age_hours=24,
    )
    assert not scanner_is_ready(
        engine="other", definitions_updated_at=now, observed_at=now, maximum_age_hours=24,
    )
    assert not scanner_is_ready(
        engine="clamav", definitions_updated_at=now.replace(tzinfo=None),
        observed_at=now, maximum_age_hours=24,
    )


def test_public_errors_and_delivery_headers_are_closed():
    assert safe_error_code("media_scanner_stale") == "media_scanner_stale"
    assert safe_error_code("ClamAV found private/file.exe") == "media_dependency_unavailable"
    inline = delivery_headers(media_type="image/png", inline_safe_derivative=True)
    assert inline["Content-Disposition"] == "inline"
    assert inline["X-Content-Type-Options"] == "nosniff"
    assert inline["Content-Security-Policy"] == "default-src 'none'; sandbox"
    original = delivery_headers(media_type="image/png", inline_safe_derivative=False)
    assert original["Content-Disposition"] == "attachment"
    assert original["Cache-Control"] == "private, no-store"
