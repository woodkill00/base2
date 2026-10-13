import json

import pytest

from scripts.python.operations_visual_evidence import (
    MANIFEST,
    VisualEvidenceError,
    build,
    validate,
)


def test_committed_visual_evidence_matches_exact_sources_and_captures():
    validate(json.loads(MANIFEST.read_text(encoding="utf-8")))
    assert len(build()["screenshots"]) == 35


def test_source_or_capture_drift_is_rejected():
    value = build()
    value["sources"][next(iter(value["sources"]))] = "0" * 64
    with pytest.raises(VisualEvidenceError, match="exact sources"):
        validate(value)


def assert_capture_dimensions(name, width, height):
    # The reviewed 200%-text full-page capture includes the restored footer
    # (5813px). Other captures retain their original height bound, and the
    # original maximum decoded-pixel budget is preserved for every capture.
    max_height = 6000 if name == "operations-center-chromium-large-text-chromium-large-text-linux.png" else 5000
    assert 300 <= width <= 2560
    assert 600 <= height <= max_height
    assert width * height <= 2560 * 5000


def test_all_captures_are_nonempty_pngs_with_bounded_dimensions():
    for name, item in build()["screenshots"].items():
        assert_capture_dimensions(name, *item["pixels"])
        assert len(item["sha256"]) == 64


@pytest.mark.parametrize("name,width,height", [
    ("operations-center-chromium-desktop-chromium-desktop-linux.png", 1280, 5001),
    ("operations-center-chromium-large-text-chromium-large-text-linux.png", 1280, 6001),
    ("operations-center-chromium-large-text-chromium-large-text-linux.png", 2560, 6000),
])
def test_oversized_captures_remain_rejected(name, width, height):
    with pytest.raises(AssertionError):
        assert_capture_dimensions(name, width, height)
