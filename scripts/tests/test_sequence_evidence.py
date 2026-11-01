"""Synthetic comparison transport tests; these are not native visual receipts."""

import copy
import hashlib
import json
import struct

import pytest

from scripts.python import sequence_evidence as sequence
from scripts.tests.test_continuous_evidence import neutral_receipt, receipt  # noqa: F401


@pytest.fixture
def comparison(receipt):  # noqa: F811
    path, native = neutral_receipt(receipt)
    # Valid PNGs are decoded by the comparator; transport verifies header/hash.
    import io

    from PIL import Image

    stream = io.BytesIO()
    Image.new("RGBA", (320, 568), (0, 0, 0, 255)).save(stream, format="PNG")
    raw = stream.getvalue()
    for row in [*native["segments"], native["focus"]["capture"]]:
        (path.parent / row["file"]).write_bytes(raw)
        row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    path.write_text(json.dumps(native))
    schedule = [
        {
            **{
                k: row[k]
                for k in (
                    "offset",
                    "max",
                    "height",
                    "inset",
                    "scale",
                    "viewport",
                    "rect",
                    "extent",
                    "start",
                    "end",
                )
            },
            "next": min(row["max"], row["offset"] + (row["end"] - row["start"]) * 0.75),
        }
        for row in native["segments"]
    ]
    binding = {k: native[k] for k in ("project", "test", "route", "state", "target")}
    binding.update(
        routeStateHash="c" * 64,
        environmentHash="d" * 64,
        dependencyHash="e" * 64,
        fixtureVersion="synthetic-v1",
        geometryVersion=1,
        pixelPolicy={"maxDiffPixelRatio": 0.01, "threshold": 0.2},
        schedule=schedule,
    )
    results = []
    for i, label in enumerate(["overview", "000", "001", "002"]):
        name = f"sequence-media-{label}-actual.png"
        (path.parent / name).write_bytes(raw)
        results.append(
            dict(
                index=i,
                label=label,
                status="missing-reference-set",
                expected=None,
                diff=None,
                actual=dict(
                    file=name,
                    bytes=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(),
                    dimensions=list(struct.unpack(">II", raw[16:24])),
                ),
            )
        )
    data = dict(
        schemaVersion=1,
        complete=True,
        kind="sequence-comparison",
        geometryVersion=1,
        sourceCommit="a" * 40,
        sourceTree="b" * 40,
        runId="1",
        attempt="1",
        binding=binding,
        manifestError="missing-reference-set",
        referenceManifestSha256=None,
        referenceManifest="e2e/media/media-release.spec.ts-snapshots/sequence-media.json",
        overlayScope="neutral-focus; known Skip overlay checked; independent unobscured review required",
        results=results,
    )
    return path.with_name("sequence-media.json"), data


def check(value):
    path, data = value
    return sequence.validate(
        json.dumps(data).encode(), path, "a" * 40, "b" * 40, "chromium-compact", "1", "1"
    )


def test_missing_expected_is_truthful_fatal_status_with_exact_actuals(comparison):
    data = check(comparison)
    assert len(sequence.images(data)) == 4
    assert all(r["expected"] is None and r["diff"] is None for r in data["results"])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["binding"].update(route="/other"),
        lambda d: d["binding"]["schedule"][0].update(end=1000),
        lambda d: d["binding"]["schedule"][0].update(extent=10000),
        lambda d: d["binding"]["schedule"][0].update(next=400),
        lambda d: d["results"][0].update(status="matched"),
        lambda d: d["results"][0].update(diff=d["results"][0]["actual"]),
        lambda d: d["results"][0]["actual"].update(file="../private.png"),
        lambda d: d["results"][0]["actual"].update(sha256="f" * 64),
        lambda d: d["results"][0]["actual"].update(dimensions=[1, 1]),
        lambda d: d["results"].pop(),
        lambda d: d.update(referenceManifest="../../private.json"),
        lambda d: d.update(overlayScope="unobscured and accepted"),
        lambda d: d.update(private="secret"),
    ],
)
def test_reject_geometry_role_identity_and_private_field_tamper(comparison, mutation):
    path, data = comparison
    data = copy.deepcopy(data)
    mutation(data)
    with pytest.raises(ValueError):
        check((path, data))


def test_reject_symlinked_continuous_receipt_before_read(comparison):
    path, _ = comparison
    native = path.with_name("continuous-media.json")
    original = native.with_name("original.json")
    native.rename(original)
    native.symlink_to(original)
    with pytest.raises(ValueError):
        check(comparison)


def test_incomplete_receipt_does_not_claim_whole_sequence(comparison):
    comparison[1]["complete"] = False
    comparison[1]["results"].pop()
    assert not check(comparison)["complete"]


@pytest.mark.parametrize(
    "suite,case,state,accepted",
    [
        ("media", "media-release-unit-chromium", "media-library", True),
        ("media", "private-unit", "media-library", False),
        ("workspace", "workspace-release-unit", "workspace-records", True),
        ("journeys", "public-journeys-public-jou-unit", "journey-contact-received", True),
        ("journeys", "other-unit", "journey-contact-received", False),
        ("volcano", "volcano-preservation-unit", "named-route", True),
        ("layout", "interaction-contract-unit", "media-library", False),
    ],
)
def test_explicit_producer_registration(suite, case, state, accepted):
    assert sequence.registered(suite, case, state) is accepted


def test_matched_roles_require_exact_reviewed_repository_manifest(
    comparison, tmp_path, monkeypatch
):
    path, data = comparison
    monkeypatch.setattr(sequence, "REPOSITORY", tmp_path)
    monkeypatch.setattr(sequence.subprocess, "check_output", lambda *a, **k: "b" * 40 + "\n")
    monkeypatch.setattr(sequence.subprocess, "run", lambda *a, **k: None)
    images = []
    for row in data["results"]:
        expected = copy.deepcopy(row["actual"])
        expected["file"] = expected["file"].replace("-actual.png", "-expected.png")
        (path.parent / expected["file"]).write_bytes(
            (path.parent / row["actual"]["file"]).read_bytes()
        )
        row.update(status="matched", expected=expected)
        images.append(
            {
                "name": expected["file"].replace("-expected.png", ".png"),
                "sha256": expected["sha256"],
            }
        )
    record = dict(
        schemaVersion=1,
        decision="approved-sequence",
        sourceCommit="a" * 40,
        sourceTree="b" * 40,
        bindingSha256=sequence.canonical_hash(data["binding"]),
        imagesSha256=sequence.canonical_hash(images),
        limitations="captured neutral state only; unrelated overlays and states excluded",
    )
    record_raw = json.dumps(record).encode()
    manifest = dict(
        schemaVersion=1,
        binding=data["binding"],
        images=images,
        review=dict(
            sourceCommit="a" * 40,
            sourceTree="b" * 40,
            recordSha256=hashlib.sha256(record_raw).hexdigest(),
        ),
    )
    manifest_raw = json.dumps(manifest).encode()
    reference = tmp_path / "react-app" / data["referenceManifest"]
    reference.parent.mkdir(parents=True)
    reference.write_bytes(manifest_raw)
    reference.with_suffix(".review.json").write_bytes(record_raw)
    data.update(
        manifestError=None, referenceManifestSha256=hashlib.sha256(manifest_raw).hexdigest()
    )
    assert check(comparison)["results"][0]["status"] == "matched"
    reference.with_suffix(".review.json").write_text("{}")
    with pytest.raises(ValueError, match="review hash"):
        check(comparison)


def test_per_state_comparisons_keep_hard_footer_assertions_and_runtime_bindings():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    scroll = (root / "react-app/e2e/scroll-target.ts").read_text()
    after = scroll.split("if (!captured) return;", 1)[1]
    assert "if (comparisonRatio !== undefined) return" not in after
    assert (
        "expect(footerOverlaps,'Persistentcontrolsmustnotoverlapvisiblefootercontent')"
        in "".join(after.split())
    )
    assert "toBeInViewport" in after
    source = (root / "react-app/e2e/sequence-reference.ts").read_text()
    for name in [
        "'public'",
        "'*.config.*'",
        "'index.html'",
        "'package*.json'",
        "'../e2e/support'",
        "'../scripts'",
    ]:
        assert name in source
    assert "!p.endsWith('.png')" not in source
    for identity in [
        "browserVersion",
        "platform()",
        "architecture:arch()",
        "kernel:release()",
        "fontsHash",
        "'fc-list'",
    ]:
        assert identity.replace(" ", "") in source.replace(" ", "")


def test_picker_legacy_mismatch_does_not_abort_ready_sequence_or_reuse():
    from pathlib import Path

    source = (Path(__file__).parents[2] / "react-app/e2e/media/media-release.spec.ts").read_text()
    picker = source.split("test('media picker", 1)[1].split("test('media library", 1)[0]
    assert picker.count("expect.soft") == 1
    assert "expect.soft(picker).toHaveScreenshot" in picker
    assert picker.index("expect.soft(picker)") < picker.index("'media-picker', picker, 0.01")
    assert picker.index("'media-picker', picker, 0.01") < picker.index("await useSelected.click()")
    assert "await expect(useSelected).toBeEnabled()" in picker
    assert "await expect(opener).toBeFocused()" in picker
    assert "1 existing media item chosen for reuse." in picker
    assert "maxDiffPixelRatio: 0.01" in picker


def test_operations_legacy_header_override_is_removed_before_genuine_sequences():
    from pathlib import Path

    source = (Path(__file__).parents[2] / "react-app/e2e/operations/operations-release.spec.ts").read_text()
    helper = source.split("async function captureCurrentRun", 1)[1].split("test.afterEach", 1)[0]
    assert "finally {" in helper
    assert "node.parentNode?.removeChild(node)" in helper
    assert helper.index("finally {") < helper.index("toHaveCSS('position', 'sticky')") < helper.index("captureScrollportExtent")
    assert source.count("position: static !important") == 1
    assert "expect.soft(page).toHaveScreenshot" in helper


def test_attempted_applicability_failure_is_captured_before_rethrow():
    from pathlib import Path

    source = (Path(__file__).parents[2] / "react-app/e2e/continuous-scroll.ts").read_text()
    block = source.split("let applicable: boolean;", 1)[1].split("const receiptName", 1)[0]
    assert block.index("ownedScreenshot(page, info,") < block.index("throw error")
    assert "Preserve the original applicability failure" in block


@pytest.mark.parametrize('raw', [b'null', b'[]', b'1', b'"private"'])
def test_invalid_root_shapes_are_validation_errors(tmp_path, raw):
    with pytest.raises(ValueError):
        sequence.validate(raw, tmp_path/'sequence-journey-contact-received.json', 'a'*40, 'b'*40)
    with pytest.raises(ValueError):
        sequence.continuous_evidence.validate(raw, tmp_path/'continuous-journey-contact-received.json', 'a'*40, 'b'*40)
