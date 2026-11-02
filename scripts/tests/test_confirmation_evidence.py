import copy
import hashlib
import json
import struct
import zlib
from pathlib import Path

import pytest

from scripts.python import confirmation_evidence as module
from scripts.python import shell_png_evidence as collector
from scripts.python import workspace_ownership


def png(w=320, h=568, filter_tag=0):
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((bytes([filter_tag]) + bytes(w * 4)) * h))
        + chunk(b"IEND", b"")
    )


def fixture(tmp_path):
    case = "workspace-release-workspac-c3eae-ons-cancel-without-mutation-chromium-compact"
    directory = tmp_path / case
    directory.mkdir()
    image = png()
    name = "workspace-confirm-publish-attempt.png"
    (directory / name).write_bytes(image)
    provenance = dict(sourceCommit="a" * 40, sourceTree="b" * 40, runId="1", attempt="1")
    sample = dict(
        state="publish",
        route="workspace",
        target="scrollport",
        focus="dismiss",
        viewport=[320, 568, 1],
        visual=[0, 0, 320, 568],
        panel=[20, 100, 280, 200],
        port=[0, 0, 320, 500],
        header=[0, 0, 320, 80],
        sticky=True,
        offset=100,
        max=600,
        scale=1,
        layout=[500, 1100, 500],
        visualScale=1,
        overscroll=False,
        dialogs=1,
    )
    data = dict(
        schemaVersion=2,
        scope="synthetic-confirmation-capture",
        **provenance,
        project="chromium-compact",
        state="publish",
        settlement=dict(probes=2, elapsed=10),
        pre=sample,
        post=copy.deepcopy(sample),
        image=dict(
            file=name,
            bytes=len(image),
            sha256=hashlib.sha256(image).hexdigest(),
            dimensions=[320, 568],
        ),
        errors=[],
        complete=True,
    )
    path = directory / "workspace-confirm-publish-capture.json"
    return path, data, provenance


def test_roundtrip_and_partial(tmp_path):
    path, d, p = fixture(tmp_path)
    assert module.registered("workspace", Path(path.parent.name) / path.name)
    assert module.validate(json.dumps(d).encode(), path, p) == d
    d.update(complete=False, errors=["capture-state-invalid"])
    d["post"]["panel"][1] = 79.999
    assert module.validate(json.dumps(d).encode(), path, p) == d
    assert collector.image_role(path.name) == "confirmation-endpoint-diagnostic"


@pytest.mark.parametrize(
    "change",
    [
        "header",
        "visual",
        "port",
        "focus",
        "state",
        "route",
        "dpr",
        "scale",
        "target",
        "unknown",
        "null",
        "negative",
        "nan",
    ],
)
def test_reject_forged_complete(tmp_path, change):
    path, d, p = fixture(tmp_path)
    if change == "null":
        d = None
    elif change == "unknown":
        d["private"] = "no"
    else:
        for key in ["pre", "post"]:
            s = d[key]
            if change == "header":
                s["header"][3] = 101
            if change == "visual":
                s["visual"][3] = 299
            if change == "port":
                s["port"][2] = 299
            if change == "focus":
                s["focus"] = "outside"
            if change == "state":
                s["state"] = "delete"
            if change == "route":
                s["route"] = "other"
            if change == "negative":
                s["panel"][2] = -1
            if change == "nan":
                s["offset"] = float("nan")
            if change == "target":
                s["target"] = "document"
        if change == "dpr":
            d["post"]["viewport"][2] = 2
        if change == "scale":
            d["post"]["scale"] = 1.001
    with pytest.raises(ValueError):
        module.validate(json.dumps(d).encode(), path, p)


def test_duplicates_missing_tamper_source_and_unknown_producer(tmp_path):
    path, d, p = fixture(tmp_path)
    raw = json.dumps(d).encode()
    with pytest.raises(ValueError):
        module.validate(raw[:-1] + b',"complete":true}', path, p)
    with pytest.raises(ValueError):
        module.validate(raw, path, {**p, "runId": "2"})
    (path.parent / d["image"]["file"]).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        module.validate(raw, path, p)
    assert not module.registered("journeys", Path(path.parent.name) / path.name)
    assert not module.registered("workspace", Path("private") / path.name)


def test_missing_capture_is_explicit_incomplete(tmp_path):
    path, d, p = fixture(tmp_path)
    d.update(image=None, complete=False, errors=["capture-missing"])
    assert module.validate(json.dumps(d).encode(), path, p) == d
    d["errors"] = []
    with pytest.raises(ValueError):
        module.validate(json.dumps(d).encode(), path, p)


def test_collector_retains_valid_diagnostic_with_failed_outcome(tmp_path):
    path, d, p = fixture(tmp_path)
    path.write_text(json.dumps(d))
    source = path.parent.parent
    sources = {suite: tmp_path / ("absent-" + suite) for suite in collector.SUITES}
    sources["workspace"] = source
    output = tmp_path.parent / (tmp_path.name + "-output")
    p.update(requestedHead="c" * 40, outcomes={s: "failure" for s in collector.SUITES})
    ownership(path, d, p)
    collector.stage(sources, output, p)
    assert len(list(output.rglob(path.name))) == 1


def ownership(path, d, p, version=2):
    states = {k: "incomplete" for k in workspace_ownership.STATES["confirmations"]}
    states["workspace-confirm-" + d["state"]] = "complete" if d["complete"] else "incomplete"
    frames = [{k: d["image"][k] for k in ("file", "sha256", "bytes")}] if d["image"] else []
    data = dict(
        schemaVersion=version,
        scope="synthetic-workspace-ownership",
        scenario="confirmations",
        **{k: p[k] for k in ("sourceCommit", "sourceTree", "runId", "attempt")},
        revoked=True,
        bodySettled=True,
        hookStarted=True,
        incomplete=True,
        coverage=states,
        errors=["coverage-incomplete"],
        frames=frames,
    )
    target = path.parent / workspace_ownership.NAME
    target.write_text(json.dumps(data))
    return target, data


@pytest.mark.parametrize(
    "change",
    [
        "sticky-null",
        "document-scale",
        "overscroll",
        "dpr999",
        "false-max",
        "zero-scale",
        "dimensions",
    ],
)
def test_matching_endpoints_cannot_forge_geometry(tmp_path, change):
    path, d, p = fixture(tmp_path)
    for s in [d["pre"], d["post"]]:
        if change == "sticky-null":
            s["header"] = None
        if change == "document-scale":
            s.update(target="document", port=None, scale=2, layout=[568, 1168, 568])
        if change == "overscroll":
            s.update(offset=1000, overscroll=True)
        if change == "dpr999":
            s["viewport"][2] = 999
        if change == "false-max":
            s["max"] = 900
        if change == "zero-scale":
            s["scale"] = 0
    if change == "dimensions":
        d["image"]["dimensions"] = [640, 1136]
    with pytest.raises(ValueError):
        module.validate(json.dumps(d).encode(), path, p)


def test_elastic_overscroll_retained_only_incomplete(tmp_path):
    path, d, p = fixture(tmp_path)
    for s in [d["pre"], d["post"]]:
        s.update(offset=-4, overscroll=True)
    d.update(complete=False, errors=["capture-state-invalid"])
    assert module.validate(json.dumps(d).encode(), path, p) == d
    d["complete"] = True
    d["errors"] = []
    with pytest.raises(ValueError):
        module.validate(json.dumps(d).encode(), path, p)


@pytest.mark.parametrize("change", ["missing", "extra", "state", "image"])
def test_capture_aware_ownership_requires_exact_endpoint_binding(tmp_path, change):
    path, d, p = fixture(tmp_path)
    path.write_text(json.dumps(d))
    target, claim = ownership(path, d, p)
    if change == "missing":
        path.unlink()
    if change == "extra":
        (path.parent / "workspace-confirm-unknown-capture.json").write_text("{}")
    if change == "state":
        d["state"] = "delete"
        path.write_text(json.dumps(d))
    if change == "image":
        claim["frames"] = []
    with pytest.raises(ValueError):
        workspace_ownership.validate(json.dumps(claim).encode(), target, p)


def test_legacy_ownership_does_not_claim_endpoint_proof(tmp_path):
    path, d, p = fixture(tmp_path)
    target, claim = ownership(path, d, p, version=1)
    assert workspace_ownership.validate(json.dumps(claim).encode(), target, p)["schemaVersion"] == 1


def test_png_complete_decode_crc_and_filter(tmp_path):
    assert module.png_dimensions(png()) == [320, 568]
    for raw in [png()[:-1], png(filter_tag=5), png()[:40] + b"x" + png()[41:]]:
        with pytest.raises(ValueError):
            module.png_dimensions(raw)


def test_four_complete_claims_without_endpoints_fail_packaging(tmp_path):
    path, d, p = fixture(tmp_path)
    target, claim = ownership(path, d, p)
    claim["coverage"] = {k: "complete" for k in workspace_ownership.STATES["confirmations"]}
    claim["errors"] = []
    claim["incomplete"] = False
    claim["frames"] = []
    for state in module.STATES:
        name = "workspace-confirm-" + state + "-attempt.png"
        raw = png()
        (path.parent / name).write_bytes(raw)
        claim["frames"].append(
            dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        )
    target.write_text(json.dumps(claim))
    sources = {s: tmp_path / ("absent-" + s) for s in collector.SUITES}
    sources["workspace"] = tmp_path
    p.update(requestedHead="c" * 40, outcomes={s: "failure" for s in collector.SUITES})
    out = tmp_path.parent / (tmp_path.name + "-out")
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, out, p)
    meta = json.loads((out / "00/provenance.json").read_text())
    assert not meta["packagingComplete"] and meta["captureCount"] == 0


def test_supported_confirmation_cannot_downgrade_obligations_to_not_required(tmp_path):
    path, d, p = fixture(tmp_path)
    target, claim = ownership(path, d, p)
    claim["coverage"] = {k: "not-required" for k in claim["coverage"]}
    claim["frames"] = []
    with pytest.raises(ValueError):
        workspace_ownership.validate(json.dumps(claim).encode(), target, p)
