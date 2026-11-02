"""Exact historical packaging semantics are weaker than full native coverage."""

import json
from pathlib import Path

import pytest

from scripts.python import historical_media_profile as profile
from scripts.python import native_archive_evidence as native
from scripts.tests.test_native_archive_evidence import PROJECT, inventory
from scripts.tests.test_screenshot_archive import git, sample  # noqa: F401


@pytest.fixture
def historical_media(sample):  # noqa: F811
    repo, _, manifest = sample
    fixtures = Path(__file__).parent / "fixtures/historical_media"
    for name, target in (
        ("producer.txt", "scripts/python/visual_matrix_artifacts.py"),
        ("workflow.txt", ".github/workflows/ci-visual-review.yml"),
    ):
        dest = repo / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((fixtures / name).read_bytes())
    git(
        repo,
        "add",
        "scripts/python/visual_matrix_artifacts.py",
        ".github/workflows/ci-visual-review.yml",
    )
    git(repo, "commit", "-m", "Exact historical producer fixtures")
    identity = {
        k: manifest[k] for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
    }
    identity.update(
        sourceCommit=git(repo, "rev-parse", "HEAD"),
        requestedHead=git(repo, "rev-parse", "HEAD"),
        sourceTree=git(repo, "rev-parse", "HEAD^{tree}"),
    )
    data = inventory()
    data.update(
        {k: str(v) for k, v in identity.items() if k != "requestedHead"},
        matrix="media",
        complete=True,
    )
    title = "media library is accessible responsive and visually reviewed"
    entry = data["projects"][PROJECT]
    entry["expectedSupportedTests"][0]["title"] = title
    member = native.directory(title, PROJECT) + "/current-media-library.png"
    entry["captures"][0]["path"] = member
    entry["parts"][0]["members"] = [member]
    entry["missingDiagnostics"] = ["media-viewport-observations.json"]
    data["originalReports"] = [
        dict(path=name, bytes=12, sha256="a" * 64)
        for name in ("source-before.json", "source-after.json", "stages.md")
    ]
    data["missingReports"] = ["operations-visual-runner.json"]
    return repo, identity, data


def test_source_pinned_missing_optional_report_preserves_real_diagnostic_gap(historical_media):
    repo, identity, data = historical_media
    raw = json.dumps(data).encode()
    with pytest.raises(ValueError, match="complete reports contradiction"):
        native.validate(raw, "inventory.json", identity)
    result = profile.classify(repo, raw, identity)
    assert result["originalPackagingComplete"] is True
    assert result["originalMissingReports"] == ["operations-visual-runner.json"]
    assert result["coverageGaps"][PROJECT]["missingDiagnostics"] == [
        "media-viewport-observations.json"
    ]
    assert (
        not result["acceptance"] and not result["runComplete"] and not result["dependencyComplete"]
    )
    assert json.dumps(data).encode() == raw


@pytest.mark.parametrize(
    "fault", ["producer", "workflow", "operations", "private", "nonpackaged", "missing-before"]
)
def test_historical_profile_is_narrow_and_does_not_relabel_contradictions(historical_media, fault):
    repo, identity, data = historical_media
    if fault in ("producer", "workflow"):
        path = next(iter(profile.SOURCES)) if fault == "producer" else list(profile.SOURCES)[1]
        with (repo / path).open("a") as f:
            f.write("\n# changed\n")
        git(repo, "add", path)
        git(repo, "commit", "-m", "Unreviewed producer")
        identity.update(
            sourceCommit=git(repo, "rev-parse", "HEAD"),
            requestedHead=git(repo, "rev-parse", "HEAD"),
            sourceTree=git(repo, "rev-parse", "HEAD^{tree}"),
        )
        data.update(sourceCommit=identity["sourceCommit"], sourceTree=identity["sourceTree"])
    elif fault == "operations":
        data["matrix"] = "operations"
    elif fault == "private":
        data["private"] = "not-approved"
    elif fault == "nonpackaged":
        data["projects"][PROJECT]["status"] = "incomplete"
    else:
        data["originalReports"] = [
            r for r in data["originalReports"] if r["path"] != "source-before.json"
        ]
        data["missingReports"].append("source-before.json")
    with pytest.raises(ValueError):
        profile.classify(repo, json.dumps(data).encode(), identity)


def test_explicit_local_envelope_dispatch_preserves_original_gaps(historical_media, tmp_path):
    from scripts.python import screenshot_archive as a
    from scripts.python import typed_archive_support as typed

    repo, identity, data = historical_media
    raw = json.dumps(data).encode()
    sha = a.digest(raw)
    root = tmp_path / "objects-root"
    (root / "objects").mkdir(parents=True)
    (root / "objects" / f"{sha}.json").write_bytes(raw)
    entry = dict(
        path=f"objects/{sha}.json",
        sha256=sha,
        bytes=len(raw),
        artifactId=33,
        archiveSha256="b" * 64,
        member="inventory.json",
        archiveChain=[
            dict(
                member="inventory.json", sha256=sha, hashBasis="externally-verified-original-member"
            )
        ],
    )
    with pytest.raises(ValueError, match="complete reports contradiction"):
        typed.load_native_envelopes([entry], identity, root)
    classifications = {}
    loaded = typed.load_native_envelopes(
        [entry],
        identity,
        root,
        repo=repo,
        historical_profiles={sha: "historical-media-packaging-a131afa-bd57b58"},
        classifications=classifications,
    )
    assert loaded[0][1] == data
    assert classifications[sha]["dependencyComplete"] is False
    assert classifications[sha]["coverageGaps"][PROJECT]["missingDiagnostics"]
    assert (root / entry["path"]).read_bytes() == raw
    with pytest.raises(ValueError, match="explicit historical"):
        typed.load_native_envelopes(
            [entry],
            identity,
            root,
            repo=repo,
            historical_profiles={sha: "unknown"},
            classifications={},
        )
