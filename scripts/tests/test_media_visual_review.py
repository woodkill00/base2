from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "specs/105-universal-media-library"
SNAPSHOTS = ROOT / "react-app/e2e/media/media-release.spec.ts-snapshots"


def test_media_visual_review_is_schema_valid_exact_and_source_bound():
    schema = json.loads((ROOT / "shared/schemas/media-visual-review-v1.schema.json").read_text())
    review = json.loads((FEATURE / "visual-review.json").read_text())
    assert schema["additionalProperties"] is False
    assert set(review) == set(schema["required"])
    assert review["schemaVersion"] == schema["properties"]["schemaVersion"]["const"]
    assert re.fullmatch(schema["properties"]["sourceCommit"]["pattern"], review["sourceCommit"])
    expected_assertions = set(schema["properties"]["assertions"]["required"])
    assert set(review["assertions"]) == expected_assertions
    assert all(value == "pass" for value in review["assertions"].values())
    member_pattern = schema["properties"]["screenshots"]["items"]["pattern"]
    assert len(review["screenshots"]) == 24 == len(set(review["screenshots"]))
    assert all(re.fullmatch(member_pattern, member) for member in review["screenshots"])
    assert review["status"] == "accepted"
    assert review["screenshots"] == sorted(review["screenshots"])
    assert {path.name for path in SNAPSHOTS.glob("*.png")} == set(review["screenshots"])
    subprocess.run(
        ["git", "cat-file", "-e", f'{review["sourceCommit"]}^{{commit}}'],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", review["sourceCommit"], "HEAD"],
        cwd=ROOT,
        check=True,
    )
    reviewed_surfaces = [
        "react-app/src/pages/MediaLibrary.jsx",
        "react-app/src/components/media/MediaPicker.jsx",
        "react-app/src/styles/media-library.css",
        "react-app/e2e/media/media-release.spec.ts",
        "react-app/playwright.media-release.config.mjs",
        "react-app/e2e/media/media-release.spec.ts-snapshots",
    ]
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", review["sourceCommit"], "HEAD", "--", *reviewed_surfaces],
        cwd=ROOT,
        check=False,
    )
    assert unchanged.returncode == 0, "visual review predates a media UI or proof change"
    for diff_args in (["git", "diff", "--quiet"], ["git", "diff", "--cached", "--quiet"]):
        clean = subprocess.run(
            [*diff_args, "--", *reviewed_surfaces],
            cwd=ROOT,
            check=False,
        )
        assert clean.returncode == 0, "uncommitted media UI or proof change is not visually reviewed"
    for member in review["screenshots"]:
        committed = subprocess.run(
            ["git", "cat-file", "-e", f'{review["sourceCommit"]}:react-app/e2e/media/media-release.spec.ts-snapshots/{member}'],
            cwd=ROOT,
            check=False,
        )
        assert committed.returncode == 0, f"unbound screenshot: {member}"
