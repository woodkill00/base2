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
    assert len(build()["screenshots"]) == 15


def test_source_or_capture_drift_is_rejected():
    value = build()
    value["sources"][next(iter(value["sources"]))] = "0" * 64
    with pytest.raises(VisualEvidenceError, match="exact sources"):
        validate(value)


def test_all_captures_are_nonempty_pngs_with_bounded_dimensions():
    for item in build()["screenshots"].values():
        width, height = item["pixels"]
        assert 300 <= width <= 2560
        assert 600 <= height <= 5000
        assert len(item["sha256"]) == 64
