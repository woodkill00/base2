import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

from scripts.python import visual_matrix_artifacts as module

ROOT = Path(__file__).resolve().parents[2]
PNG = b"\x89PNG\r\n\x1a\n" + b"unit fixture, not native evidence"


def fixture(tmp_path):
    source = tmp_path / "native"
    source.mkdir()
    before = {"sourceCommit": "a" * 40, "sourceTree": "b" * 40,
              "runId": "123", "attempt": "1", "matrix": "operations",
              "expectedTests": [{"project": p, "title": "unit fixture", "expectedStatus": "passed"}
                                for p in ["chromium-desktop", "chromium-light"]]}
    (source / "source-before.json").write_text(json.dumps(before))
    (source / "source-after.json").write_text('{"nativeOutcome":"failure"}')
    case = source / "test-results" / "operations-case-chromium-desktop"
    case.mkdir(parents=True)
    (case / "current-operations.png").write_bytes(PNG)
    (case / "operations-actual.png").write_bytes(PNG)
    (case / "trace.zip").write_bytes(b"excluded")
    (case / "video.webm").write_bytes(b"excluded")
    return source, case, tmp_path / "bounded"


def test_exact_pngs_and_original_failed_reports_with_empty_project_visible(tmp_path):
    source, case, output = fixture(tmp_path)
    original = {p: p.read_bytes() for p in source.rglob("*") if p.is_file()}
    result = module.stage(source, output)
    assert not result["errors"]
    assert result["projects"]["chromium-light"]["status"] == "incomplete"
    assert result["projects"]["chromium-light"]["captures"] == []
    assert result["projects"]["chromium-light"]["minimumCaptureShortfall"] == 1
    assert result["projects"]["chromium-desktop"]["captureCoverage"] == "requires-review"
    assert "operations-visual-runner.json" in result["missingReports"]
    with zipfile.ZipFile(output / "chromium-desktop.zip") as z:
        assert len(z.namelist()) == 2
        assert all(z.read(n) == PNG for n in z.namelist())
        assert all(n.endswith(".png") for n in z.namelist())
    with zipfile.ZipFile(output / "metadata.zip") as z:
        assert z.read("source-after.json") == b'{"nativeOutcome":"failure"}'
        assert json.loads(z.read("inventory.json")) == result
    assert all(p.read_bytes() == raw for p, raw in original.items())
    assert all(p.stat().st_size < 32 * 1024 * 1024 for p in output.iterdir())
    capture = result["projects"]["chromium-desktop"]["captures"][0]
    assert capture["sha256"] == hashlib.sha256(PNG).hexdigest()
    with pytest.raises(ValueError, match="fresh"):
        module.stage(source, output)


@pytest.mark.parametrize("kind", ["file", "case", "source"])
def test_symlinks_rejected_without_copying_target(tmp_path, kind):
    source, case, output = fixture(tmp_path)
    if kind == "file":
        (case / "test-failed-1.png").symlink_to(case / "current-operations.png")
    elif kind == "case":
        (source / "test-results" / "other-chromium-light").symlink_to(case, target_is_directory=True)
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(source, target_is_directory=True)
        with pytest.raises(ValueError, match="symlink"):
            module.stage(alias, output)
        return
    result = module.stage(source, output)
    assert any("symlink" in e for e in result["errors"])
    assert not list(output.glob("chromium-*.zip"))


def test_traversal_and_untrusted_project_names(tmp_path):
    source, _, output = fixture(tmp_path)
    with pytest.raises(ValueError, match="traversal"):
        module.stage(source / ".." / "native", output)
    before = json.loads((source / "source-before.json").read_text())
    before["expectedTests"] = [{"project": "../escape"}]
    (source / "source-before.json").write_text(json.dumps(before))
    with pytest.raises(ValueError, match="projects"):
        module.stage(source, output)


@pytest.mark.parametrize("change", ["oversize", "unknown", "signature"])
def test_incomplete_inputs_never_truncated_or_reported_packaged(tmp_path, monkeypatch, change):
    source, case, output = fixture(tmp_path)
    if change == "oversize":
        monkeypatch.setattr(module, "PNG_BUDGET", len(PNG))
    elif change == "unknown":
        (case / "private.png").write_bytes(PNG)
    else:
        (case / "current-operations.png").write_bytes(b"not PNG")
    result = module.stage(source, output)
    assert result["errors"]
    assert result["projects"]["chromium-desktop"]["status"] == "incomplete"
    assert not (output / "chromium-desktop.zip").exists()
    assert (output / "metadata.zip").is_file()


def test_missing_test_results_stays_incomplete(tmp_path):
    source, case, output = fixture(tmp_path)
    for p in case.iterdir():
        p.unlink()
    case.rmdir()
    case.parent.rmdir()
    result = module.stage(source, output)
    assert all(p["status"] == "incomplete" for p in result["projects"].values())
    assert not list(output.glob("chromium-*.zip"))


def test_diagnostic_only_project_does_not_hide_missing_current_capture(tmp_path):
    source, case, output = fixture(tmp_path)
    (case / "current-operations.png").unlink()
    result = module.stage(source, output)
    project = result["projects"]["chromium-desktop"]
    assert project["status"] == "packaged"
    assert project["captureCoverage"] == "incomplete"
    assert project["minimumCaptureShortfall"] == 1


def test_zip_overhead_limit_is_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ZIP_BUDGET", 10)
    with pytest.raises(ValueError, match="ZIP"):
        module.archive(tmp_path / "bounded.zip", {"capture.png": PNG})
    assert not list(tmp_path.iterdir())


def test_workflow_retains_original_and_failure_propagation():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci-visual-review.yml").read_text())
    steps = workflow["jobs"]["visual-review"]["steps"]
    indexed = {s["id"]: s for s in steps if "id" in s}
    assert indexed["evidence"]["if"] == "always()"
    assert indexed["evidence"]["with"]["path"].splitlines()[0] == "${{ env.VISUAL_OUTPUT }}/test-results/"
    assert steps.index(indexed["evidence"]) < steps.index(indexed["bounded"])
    assert indexed["bounded"]["if"] == "always() && steps.before.outcome == 'success'"
    assert not any("continue-on-error" in s for s in steps)
    assert "||" not in indexed["matrix"]["run"]
    assert "--update-snapshots=none" in indexed["matrix"]["run"]
    projects = set()
    for mode in ("operations", "media"):
        config = (ROOT / f"react-app/playwright.{mode}-release.config.mjs").read_text()
        projects.update(re.findall(r"(?:chromium\(\s*|name:\s*)'([^']+)'", config))
    uploads = [s for s in steps if s.get("name", "").startswith("Retain bounded ")]
    paths = {s["with"]["path"].split("/")[-1] for s in uploads}
    assert paths == {"metadata.zip", *(p + ".zip" for p in projects)}
    for step in uploads:
        assert step["if"] == "always() && steps.before.outcome == 'success'"
        assert step["with"]["retention-days"] == 7
        assert len(step["uses"].split("@")[1]) == 40
    # A failing matrix remains a failing shell command; diagnostic packaging
    # is a separate always() step, with no success override.
    failed = subprocess.run(["bash", "-e", "-c", indexed["matrix"]["run"]],
                            env={"REVIEW_LABEL": "unknown"}, capture_output=True)
    assert failed.returncode == 2
    backend = (ROOT / ".github/workflows/ci-backend.yml").read_text()
    assert "scripts/tests/test_visual_matrix_artifacts.py" in backend
    assert "scripts/tests/test_operations_motion_cascade.py" in backend


def media_observation_fixture(tmp_path):
    source, old_case, output = fixture(tmp_path)
    before = json.loads((source / "source-before.json").read_bytes())
    before["matrix"] = "media"
    for declared in before["expectedTests"]:
        declared["title"] = module.MEDIA_TEST
    (source / "source-before.json").write_text(json.dumps(before))
    case = old_case.with_name(module.MEDIA_CASE + "chromium-desktop")
    old_case.rename(case)
    rectangle = {"x": 0, "y": 0, "width": 10, "height": 10,
                 "top": 0, "right": 10, "bottom": 10, "left": 0}
    target = {"kind": "filename", "rect": rectangle, "centerInViewport": True,
              "centerUnobstructed": False, "overlappingControls": ["base2-scroll-ascend"]}
    body = {
        "schemaVersion": 1, "fixtureScope": "synthetic-project-tests",
        "project": "chromium-desktop", "test": module.MEDIA_TEST,
        "scope": "Diagnostic viewport observations; not visual acceptance.",
        "viewportObservations": [
            {"cardIndex": index, "scrollY": 200, "viewport": [1440, 1000],
             "controls": [{"id": "base2-scroll-ascend", "rect": rectangle}],
             "targets": [target.copy() for _ in range(5)]} for index in (0, 2, 4)
        ],
    }
    for index in (0, 2, 4):
        (case / f"current-media-library-viewport-{index}.png").write_bytes(PNG)
    observation = case / module.OBSERVATION_NAME
    observation.write_text(json.dumps(body))
    return source, case, output, observation, body


def test_allowlisted_observation_bytes_and_hash_preserve_native_failure(tmp_path):
    source, case, output, observation, _ = media_observation_fixture(tmp_path)
    raw = observation.read_bytes()
    # Deliberately invalid/private-shaped adjacent JSON must never be read/exported.
    (case / "private.json").write_text('{"private":"unit sentinel"}')
    (case / "arbitrary-report.json").write_text("not JSON")
    result = module.stage(source, output)
    assert not result["errors"]
    name = observation.relative_to(source / "test-results").as_posix()
    diagnostic = result["projects"]["chromium-desktop"]["diagnostics"]
    assert diagnostic == [{"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]
    assert result["projects"]["chromium-desktop"]["missingDiagnostics"] == []
    assert result["projects"]["chromium-light"]["missingDiagnostics"] == [module.OBSERVATION_NAME]
    with zipfile.ZipFile(output / "chromium-desktop.zip") as z:
        assert z.read(name) == raw
        assert [n for n in z.namelist() if n.endswith(".json")] == [name]
    with zipfile.ZipFile(output / "metadata.zip") as z:
        assert z.read("source-after.json") == b'{"nativeOutcome":"failure"}'
        assert json.loads(z.read("inventory.json"))["projects"]["chromium-desktop"]["diagnostics"] == diagnostic
    assert observation.read_bytes() == raw


@pytest.mark.parametrize("change", [
    "oversize", "private-field", "target-text", "wrong-project", "wrong-fixture",
    "unknown-control", "nonfinite", "wrong-case", "symlink", "missing-png", "duplicate-key",
])
def test_unsafe_observations_are_never_exported(tmp_path, change):
    source, case, output, observation, body = media_observation_fixture(tmp_path)
    if change == "oversize":
        observation.write_bytes(b" " * (module.OBSERVATION_BUDGET + 1))
    elif change == "symlink":
        observation.unlink()
        observation.symlink_to(source / "source-after.json")
    elif change == "wrong-case":
        case.rename(case.with_name("other-case-chromium-desktop"))
    elif change == "missing-png":
        (case / "current-media-library-viewport-2.png").unlink()
    elif change == "duplicate-key":
        observation.write_text('{"scope":"unit private sentinel",' + observation.read_text()[1:])
    else:
        if change == "private-field":
            body["private"] = "unit sentinel"
        elif change == "target-text":
            body["viewportObservations"][0]["targets"][0]["text"] = "unit sentinel"
        elif change == "wrong-project":
            body["project"] = "chromium-light"
        elif change == "wrong-fixture":
            body["fixtureScope"] = "real-user-data"
        elif change == "unknown-control":
            body["viewportObservations"][0]["controls"][0]["id"] = "private-control"
        elif change == "nonfinite":
            body["viewportObservations"][0]["scrollY"] = float("nan")
        observation.write_text(json.dumps(body))
    result = module.stage(source, output)
    assert result["errors"]
    assert not (output / "chromium-desktop.zip").exists()
    with zipfile.ZipFile(output / "metadata.zip") as z:
        assert z.read("source-after.json") == b'{"nativeOutcome":"failure"}'


def test_native_persists_same_safe_observation_as_attachment():
    source = (ROOT / "react-app/e2e/media/media-release.spec.ts").read_text()
    assert "testInfo.outputPath('media-viewport-observations.json')" in source
    assert "body: observationBytes" in source
    assert "fixtureScope: 'synthetic-project-tests'" in source
    assert "text: target.textContent" not in source
    assert "name: control.getAttribute('aria-label')" not in source


def test_v2_visible_other_card_geometry_is_retained_but_bounded(tmp_path):
    source, case, output, observation, body = media_observation_fixture(tmp_path)
    body['schemaVersion'] = 2
    for row in body['viewportObservations']:
        row['targets'] = [{**target, 'cardIndex': card, 'targetIndex': index}
                          for card in range(5) for index, target in enumerate(row['targets'])]
    observation.write_text(json.dumps(body))
    result = module.stage(source, output)
    assert not result['errors']
    assert len(module.observations(observation.read_bytes(), 'chromium-desktop')['viewportObservations'][0]['targets']) == 25


@pytest.mark.parametrize('mutation', ['duplicate', 'card', 'target', 'private', 'overflow'])
def test_v2_rejects_invalid_visible_card_identity(tmp_path, mutation):
    _, _, _, _, body = media_observation_fixture(tmp_path)
    body['schemaVersion'] = 2
    for row in body['viewportObservations']:
        row['targets'] = [{**target, 'cardIndex': 4, 'targetIndex': index}
                          for index, target in enumerate(row['targets'])]
    targets = body['viewportObservations'][0]['targets']
    if mutation == 'duplicate':
        targets.append(targets[0].copy())
    elif mutation == 'card':
        targets[0]['cardIndex'] = 5
    elif mutation == 'target':
        targets[0]['targetIndex'] = -1
    elif mutation == 'private':
        targets[0]['filename'] = 'must-not-export'
    else:
        targets.extend([targets[0]] * 26)
    with pytest.raises(ValueError):
        module.observations(json.dumps(body).encode(), 'chromium-desktop')


def test_clear_center_does_not_erase_control_corner_overlap(tmp_path):
    _, _, _, _, body = media_observation_fixture(tmp_path)
    body['schemaVersion'] = 2
    for row in body['viewportObservations']:
        row['targets'] = [{**target, 'cardIndex': 4, 'targetIndex': index,
                           'kind': 'action', 'centerUnobstructed': True}
                          for index, target in enumerate(row['targets'])]
    checked = module.observations(json.dumps(body).encode(), 'chromium-desktop')
    for row in checked['viewportObservations']:
        assert all(target['centerUnobstructed'] is True for target in row['targets'])
        assert all(target['overlappingControls'] == ['base2-scroll-ascend']
                   for target in row['targets'])


def test_v3_retains_explicit_scrollport_clip_geometry(tmp_path):
    _, _, _, _, body = media_observation_fixture(tmp_path)
    body['schemaVersion'] = 3
    for row in body['viewportObservations']:
        row['contentViewport'] = {'x': 0, 'y': 0, 'width': 320, 'height': 500,
                                  'left': 0, 'top': 0, 'right': 320, 'bottom': 500}
        row['targets'] = [{**target, 'cardIndex': 4, 'targetIndex': index}
                          for index, target in enumerate(row['targets'])]
    checked = module.observations(json.dumps(body).encode(), 'chromium-desktop')
    assert checked['viewportObservations'][0]['contentViewport']['bottom'] == 500
    body['viewportObservations'][0]['contentViewport']['private'] = 'not allowed'
    with pytest.raises(ValueError):
        module.observations(json.dumps(body).encode(), 'chromium-desktop')


def test_v4_distinguishes_header_occlusion_without_rewriting_old_geometry(tmp_path):
    _, _, _, _, body = media_observation_fixture(tmp_path)
    body['schemaVersion'] = 4
    for row in body['viewportObservations']:
        row['contentViewport'] = {'x': 0, 'y': 0, 'width': 320, 'height': 500,
                                  'left': 0, 'top': 0, 'right': 320, 'bottom': 500}
        row['unobscuredContentViewport'] = {'x': 0, 'y': 100, 'width': 320, 'height': 400,
                                  'left': 0, 'top': 100, 'right': 320, 'bottom': 500}
        row['targets'] = [{**target, 'cardIndex': 4, 'targetIndex': index,
                           'centerInViewport': True, 'centerInUnobscuredContent': False,
                           'centerUnobstructed': False}
                          for index, target in enumerate(row['targets'])]
    checked = module.observations(json.dumps(body).encode(), 'chromium-desktop')
    row = checked['viewportObservations'][0]
    assert row['targets'][0]['centerInViewport'] is True
    assert row['targets'][0]['centerInUnobscuredContent'] is False
    assert row['targets'][0]['overlappingControls'] == ['base2-scroll-ascend']
    body['viewportObservations'][0]['unobscuredContentViewport']['top'] = -1
    with pytest.raises(ValueError):
        module.observations(json.dumps(body).encode(), 'chromium-desktop')


@pytest.mark.parametrize('count', [3, 4])
def test_v4_all_persistent_control_overlaps_survive_bounded_roundtrip(tmp_path, count):
    source, _, output, observation, body = media_observation_fixture(tmp_path)
    body['schemaVersion'] = 4
    controls = ['base2-scroll-ascend', 'base2-scroll-descend',
                'base2-left-menu-toggle', 'base2-right-utility-toggle'][:count]
    for row in body['viewportObservations']:
        rect = row['controls'][0]['rect']
        row['contentViewport'] = rect.copy()
        row['unobscuredContentViewport'] = rect.copy()
        row['controls'] = [{'id': name, 'rect': rect.copy()} for name in controls]
        row['targets'] = [{**target, 'cardIndex': 0, 'targetIndex': index,
                           'centerInUnobscuredContent': True, 'overlappingControls': controls.copy()}
                          for index, target in enumerate(row['targets'])]
    raw = json.dumps(body).encode()
    observation.write_bytes(raw)
    result = module.stage(source, output)
    assert result['errors'] == []
    name = observation.relative_to(source / 'test-results').as_posix()
    with zipfile.ZipFile(output / 'chromium-desktop.zip') as archive:
        assert archive.read(name) == raw
        assert json.loads(archive.read(name))['viewportObservations'][0]['targets'][0]['overlappingControls'] == controls
    body['viewportObservations'][0]['targets'][0]['overlappingControls'] = [controls[0], controls[0]]
    with pytest.raises(ValueError):
        module.observations(json.dumps(body).encode(), 'chromium-desktop')
