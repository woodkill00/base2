"""Versioned diagnostic registrations, separate from source-pinned historical v1 data.

A registry is retention metadata, never acceptance. Image closure is reconstructed
from exact archived manifests across parts; only original receipt bytes are stored.
Unknown outcomes are not inferred from filenames or absence of errors.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
from pathlib import Path

from scripts.python import (
    confirmation_evidence,
    continuous_evidence,
    sequence_evidence,
    visual_matrix_artifacts,
    workspace_checkpoints,
    workspace_ownership,
)
from scripts.python import screenshot_archive as a

MAX_BYTES = 16 * 1024 * 1024
MATRIX_PROJECTS = r"(?:chromium-(?:compact|phone-dpr3|landscape-touch|tablet|desktop|ultrawide|large-text|400-zoom|light|high-contrast|german|rtl|reduced-motion)|firefox-desktop|webkit-desktop)"
FAMILIES = {
    "continuous": {1, 2},
    "sequence": {1},
    "ownership": {1, 2},
    "checkpoint": {1},
    "confirmation": {2},
    "media-geometry": {1, 2, 3, 4},
}


def strict(raw):
    a.require(0 < len(raw) <= MAX_BYTES, "typed metadata size bound")
    value = sequence_evidence.strict_json(raw)
    a.require(type(value) is dict, "typed metadata root")
    return value


def fields(value, keys):
    a.require(type(value) is dict and set(value) == set(keys.split()), "typed fields")


def bound_bytes(root, entry):
    path = a.safe_path(root, entry["path"])
    a.require(path.is_file() and 0 < path.stat().st_size <= MAX_BYTES, "typed object bound")
    raw = path.read_bytes()
    a.require(
        type(entry["bytes"]) is int
        and len(raw) == entry["bytes"]
        and a.digest(raw) == entry["sha256"],
        "typed object integrity",
    )
    return raw


def standard_producer_title(suite, case, project):
    """Finite authored producers that actually emit typed continuous evidence.

    Layout-only PNG producers have no typed receipt registration; arbitrary titles
    never fall through to an operations producer. No historical code is executed.
    """
    entries = []
    if suite == "volcano" and project == "chromium":
        guest = [
            "/signup",
            "/login",
            "/about",
            "/contact",
            "/search",
            "/privacy",
            "/ar/about",
            "/not-a-real-page",
            "/terms",
            "/accessibility",
            "/journal",
            "/events",
            "/portfolio",
            "/portfolio/example",
            "/blog",
            "/blog/example",
            "/docs",
            "/docs/example",
            "/verify-email",
            "/forgot-password",
            "/reset-password",
            "/de/about",
        ]
        authenticated = [
            "/dashboard",
            "/workspace",
            "/media",
            "/operations",
            "/admin",
            "/accept-invitation",
            "/account",
            "/settings/profile",
        ]
        titles = [
            f"Volcano {kind} {route} at {width}px"
            for kind, routes in (
                ("guest route", guest),
                ("authenticated route", authenticated),
                ("empty auth errors", ["/signup", "/login"]),
            )
            for route in routes
            for width in (390, 1440)
        ]
        titles += [
            f"Volcano guest remains denied {route}"
            for route in ["/workspace", "/media", "/operations", "/admin", "/settings/profile"]
        ]
        titles += [
            f"Volcano explicit light preference and 200% zoom {route}"
            for route in ("/signup", "/ar/about")
        ]
        titles += [f"original Volcano reference at {width}px" for width in (390, 1440)]
        titles += [
            f"reserved movement space {mode}"
            for mode in [
                "compact",
                "landscape",
                "desktop",
                "rtl",
                "rtl-large-text",
                "forced",
                "zoom",
            ]
        ]
        entries = [("volcano-preservation", title, title) for title in titles]
    elif suite == "settings" and project in {
        "chromium-phone-dpr3",
        "chromium-landscape-touch",
        "chromium-tablet",
        "chromium-ultrawide",
        "chromium-large-text",
        "chromium-400-percent-reflow",
        "chromium-light",
        "chromium-high-contrast",
        "chromium-high-contrast-light",
        "firefox-desktop",
        "webkit-mobile",
    }:
        title = "release profile remains readable, reachable, accessible, and visually stable"
        entries = [("settings-release", title, title)]
    elif suite == "journeys" and project in {"chromium", "firefox", "webkit"}:
        title = "contact missing service fails visibly and retry sends exactly once"
        # Only 390px emits the continuous/sequence contact receipt.
        entries = [("public-journeys", "public journeys 390px " + title, title)]
    for prefix, title_path, title in entries:
        value = (
            prefix
            + "-"
            + re.sub(r"[\x00-\x2C\x2E-\x2F\x3A-\x40\x5B-\x60\x7B-\x7F]+", "-", title_path)
        )
        if len(value) > 60:
            value = (
                value[:26] + "-" + hashlib.sha1(value.encode()).hexdigest()[:5] + "-" + value[-27:]
            )
        if value + "-" + project == case:
            return title
    return None


def producer_title(suite, case, project):
    # Existing closed workspace scenarios include historical unsplit corpus.
    if suite == "workspace":
        if workspace_ownership.project_for_case(case) == project:
            return workspace_ownership.TITLES[workspace_ownership.scenario_for_case(case)]
        return None
    if suite in ("media", "operations"):
        titles = {
            "media": [
                "media detail preserves safe preview usage and consequence context",
                "media picker is visually and keyboard contained in a real workflow",
                "media library is accessible responsive and visually reviewed",
            ],
            "operations": [
                "operations center is accessible responsive and visually stable",
                "operations center shows truthful empty and failure states",
                "operations center exposes stale, reauthentication, and read-only recovery states",
            ],
        }
        from scripts.python.archive_support import directory

        if re.fullmatch(MATRIX_PROJECTS, project):
            return next(
                (title for title in titles[suite] if directory(title, project) == case), None
            )
    return standard_producer_title(suite, case, project)


def validate_receipt(raw, path, family, version, bundle, repo):
    data = strict(raw)
    a.require(
        type(data.get("schemaVersion")) is int
        and data["schemaVersion"] == version
        and version in FAMILIES.get(family, set()),
        "unsupported typed family/version",
    )
    suite, case, project = (bundle[k] for k in ("suite", "case", "project"))
    provenance = {k: str(bundle[k]) for k in ("sourceCommit", "sourceTree", "runId", "attempt")}
    args = (raw, path, bundle["sourceCommit"], bundle["sourceTree"])
    kwargs = dict(project=project, run=provenance["runId"], attempt=provenance["attempt"])
    title = producer_title(suite, case, project)
    if family in {"continuous", "media-geometry"}:
        a.require(data.get("test") == title, "typed receipt test mismatch")
    if family == "sequence":
        a.require(
            type(data.get("binding")) is dict and data["binding"].get("test") == title,
            "typed sequence test mismatch",
        )
    if family == "continuous":
        match = continuous_evidence.NAME.fullmatch(path.name)
        a.require(match is not None, "continuous receipt name")
        state = data.get("state")
        a.require(
            state == "current" or sequence_evidence.registered(suite, case, state),
            "unregistered continuous state",
        )
        return continuous_evidence.validate(*args, **kwargs)
    if family == "sequence":
        match = sequence_evidence.NAME.fullmatch(path.name)
        a.require(
            match is not None and sequence_evidence.registered(suite, case, match[1]),
            "unregistered sequence state",
        )
        return sequence_evidence.validate(
            *args, **kwargs, reference_source=bundle["sourceCommit"], repository=repo
        )
    if family == "ownership":
        a.require(
            workspace_ownership.registered(suite, Path(case) / path.name), "ownership producer"
        )
        return workspace_ownership.validate(raw, path, provenance)
    if family == "checkpoint":
        a.require(
            workspace_checkpoints.registered(suite, Path(case) / path.name), "checkpoint producer"
        )
        return workspace_checkpoints.validate(raw, case)
    if family == "confirmation":
        a.require(
            suite == "workspace"
            and workspace_ownership.scenario_for_case(case) == "confirmations"
            and confirmation_evidence.NAME.fullmatch(path.name),
            "confirmation producer",
        )
        return confirmation_evidence.validate(raw, path, provenance)
    a.require(
        family == "media-geometry"
        and suite == "media"
        and case.startswith("media-release-media-librar-1b4ce-")
        and path.name == visual_matrix_artifacts.OBSERVATION_NAME,
        "geometry producer",
    )
    data = visual_matrix_artifacts.observations(raw, project)
    for row in data["viewportObservations"]:
        capture = path.parent / f"current-media-library-viewport-{row['cardIndex']}.png"
        a.require(capture.is_file(), "observation missing corresponding viewport PNG")
        a.png(capture.read_bytes())
    return data


def native_envelope_binding(entry, envelope, data, frames=None):
    """Bind a source-less diagnostic to an original source/run envelope descriptor.

    This is identity evidence, not a claim that checkpoint events certify pixels.
    The caller separately validates receipt semantics and linked image closure.
    """
    member = entry["member"]
    if Path(envelope["member"]).name == "provenance.json":
        a.require(
            entry["archiveChain"][:-1] == envelope["archiveChain"][:-1],
            "typed native shard container mismatch",
        )
        prefix = Path(envelope["member"]).parent
        try:
            member = str(Path(member).relative_to(prefix))
        except ValueError as error:
            raise ValueError("typed native shard prefix mismatch") from error

        a.require(
            entry["artifactId"] == envelope["artifactId"]
            and entry["archiveSha256"] == envelope["archiveSha256"],
            "typed native shard archive mismatch",
        )
        expected_role = {
            "checkpoint": "workspace-phase-diagnostic",
            "media-geometry": "media-viewport-diagnostic",
        }[entry["family"]]
        candidates = [
            r for r in data["diagnostics"] if r["path"] == member and r["role"] == expected_role
        ]
    else:
        a.require(Path(envelope["member"]).name == "inventory.json", "typed native envelope name")
        candidates = [
            r
            for project in data["projects"].values()
            for r in project["diagnostics"]
            if r["path"] == member
        ]
        a.require(len(candidates) == 1, "typed native diagnostic descriptor")
        parts = [
            r
            for project in data["projects"].values()
            for r in project["parts"]
            if r["path"] == candidates[0]["archive"]
        ]
        a.require(
            len(parts) == 1
            and any(
                link["member"] == parts[0]["path"] and link["sha256"] == parts[0]["sha256"]
                for link in entry["archiveChain"][:-1]
            ),
            "typed native diagnostic part binding",
        )
    if entry["family"] == "media-geometry" and frames is not None:
        producer = str(Path(member).parent)
        if Path(envelope["member"]).name == "provenance.json":
            parts = Path(member).parts
            a.require(len(parts) == 3 and parts[0] == "media_hc", "typed geometry source root")
            a.require(
                producer_title("media", parts[1], "chromium-high-contrast"),
                "typed geometry producer",
            )
            captures = [
                r
                for r in data["captures"]
                if r["sourceRoot"] == parts[0] and str(Path(r["path"]).parent) == producer
            ]
        else:
            captures = [
                r
                for project in data["projects"].values()
                for r in project["captures"]
                if str(Path(r["path"]).parent) == producer
            ]
        a.require(bool(captures), "typed geometry missing native captures")
        for capture in captures:
            image = frames.get(Path(capture["path"]).name)
            a.require(
                image is not None
                and len(image) == capture["bytes"]
                and a.digest(image) == capture["sha256"],
                "typed geometry native frame identity",
            )
    a.require(
        len(candidates) == 1
        and candidates[0]["bytes"] == entry["bytes"]
        and candidates[0]["sha256"] == entry["sha256"],
        "typed native diagnostic identity",
    )


def load_native_envelopes(
    entries, bundle, root, *, repo=None, historical_profiles=None, classifications=None
):
    from scripts.python import native_archive_evidence

    a.require(type(entries) is list and len(entries) <= 480, "typed native envelope count")
    result = []
    seen = set()
    for entry in entries:
        fields(entry, "path sha256 bytes artifactId archiveSha256 member archiveChain")
        digest = entry["sha256"]
        a.require(
            type(digest) is str
            and re.fullmatch("[a-f0-9]{64}", digest)
            and entry["path"] == f"objects/{digest}.json"
            and entry["path"] not in seen,
            "typed native envelope object",
        )
        seen.add(entry["path"])
        a.require(
            type(entry["artifactId"]) is int
            and entry["artifactId"] > 0
            and type(entry["archiveSha256"]) is str
            and re.fullmatch("[a-f0-9]{64}", entry["archiveSha256"]),
            "typed native envelope archive",
        )
        a.validate_chain(dict(entry, storage=entry["path"]))
        name = Path(entry["member"]).name
        a.require(name in {"inventory.json", "provenance.json"}, "typed native envelope family")
        raw = bound_bytes(root, entry)
        selected = (historical_profiles or {}).get(digest)
        if selected is not None:
            from scripts.python import historical_media_profile

            a.require(
                repo is not None
                and classifications is not None
                and name == "inventory.json"
                and selected == "historical-media-packaging-a131afa-bd57b58",
                "explicit historical MEDIA profile",
            )
            classification = historical_media_profile.classify(repo, raw, bundle)
            classifications[digest] = classification
            data = strict(raw)
        else:
            data = native_archive_evidence.validate(raw, name, bundle)
        result.append((entry, data))
    return result


def load_native_reports(entries, envelopes, bundle, root):
    """Require exact original report dependencies of each inventory envelope."""
    from scripts.python import native_archive_evidence as native

    a.require(type(entries) is list and len(entries) <= 4, "typed native report count")
    inventories = [
        (entry, data) for entry, data in envelopes if Path(entry["member"]).name == "inventory.json"
    ]
    expected = {}
    for envelope, data in inventories:
        for descriptor in data["originalReports"]:
            name = descriptor["path"]
            a.require(name not in expected, "ambiguous native report dependency")
            expected[name] = (envelope, descriptor)
    loaded, paths = {}, set()
    for entry in entries:
        fields(entry, "path sha256 bytes artifactId archiveSha256 member archiveChain")
        a.require(
            type(entry["artifactId"]) is int and entry["artifactId"] > 0,
            "typed native report artifact type",
        )
        name = Path(entry["member"]).name
        a.require(name in expected and name not in loaded, "unexpected native report dependency")
        envelope, descriptor = expected[name]
        suffix = "md" if name == "stages.md" else "json"
        a.require(
            entry["path"] == f"objects/{descriptor['sha256']}.{suffix}"
            and entry["sha256"] == descriptor["sha256"]
            and entry["bytes"] == descriptor["bytes"]
            and entry["artifactId"] == envelope["artifactId"]
            and entry["archiveSha256"] == envelope["archiveSha256"],
            "native report original identity",
        )
        chain = entry["archiveChain"]
        a.require(
            type(chain) is list
            and len(chain) == len(envelope["archiveChain"])
            and chain[:-1] == envelope["archiveChain"][:-1],
            "native report container chain",
        )
        fields(chain[-1], "member sha256 hashBasis")
        a.require(
            chain[-1]
            == dict(
                member=entry["member"],
                sha256=entry["sha256"],
                hashBasis="externally-verified-original-member",
            )
            and str(Path(entry["member"]).parent) == str(Path(envelope["member"]).parent),
            "native report leaf chain",
        )
        raw = bound_bytes(root, entry)
        if name == "stages.md":
            header = "| Stage | Outcome |\n| --- | --- |\n"
            tail = "\nFresh native captures require independent visual review. Declared skips are not executed checks. No whole-project or release acceptance is granted.\n"
            pattern = (
                re.escape(header)
                + "".join(
                    re.escape("| " + stage + " | ")
                    + "(?:success|failure|cancelled|skipped|not-run)"
                    + re.escape(" |\n")
                    for stage in [
                        "SOURCE",
                        "INSTALL",
                        "BROWSERS",
                        "FONTS",
                        "BEFORE",
                        "MATRIX",
                        "AFTER",
                    ]
                )
                + re.escape(tail)
            )
            a.require(
                len(raw) <= 1024 and re.fullmatch(pattern, raw.decode("utf-8")),
                "native stages schema",
            )
        else:
            native.validate(raw, name, bundle)
        loaded[name] = raw
        paths.add(entry["path"])
    a.require(set(loaded) == set(expected), "missing native report dependency")
    if {"source-before.json", "source-after.json"} <= set(loaded):
        native.validate_matrix_reports(
            loaded["source-before.json"],
            loaded["source-after.json"],
            loaded.get("operations-visual-runner.json"),
            bundle,
        )
    return paths


def _validate_registry(
    repo,
    registry,
    object_root=None,
    *,
    local_context=None,
    historical_profiles=None,
    classifications=None,
):
    a.require(not historical_profiles or local_context is not None, "historical profile local-only")
    fields(registry, "schemaVersion kind bundles")
    a.require(
        type(registry["schemaVersion"]) is int
        and (registry["schemaVersion"], registry["kind"])
        == (
            (2, "typed-diagnostic-support")
            if local_context is None
            else (6, "local-zip-diagnostic-validation")
        ),
        "typed registry version",
    )
    bundles = registry["bundles"]
    a.require(type(bundles) is list and 0 < len(bundles) <= 32, "typed bundle count")
    # The existing support batch byte cap applies to unique original objects
    # across every bundle, including shared native envelopes and report leaves.
    object_sizes = {}
    for bundle in bundles:
        a.require(type(bundle) is dict, "typed bundle shape")
        for group, limit in (("receipts", 256), ("nativeEnvelopes", 480), ("nativeReports", 4)):
            entries = bundle.get(group, [])
            a.require(type(entries) is list and len(entries) <= limit, "typed object group bound")
            for entry in entries:
                a.require(
                    type(entry) is dict
                    and type(entry.get("path")) is str
                    and type(entry.get("bytes")) is int
                    and 0 < entry["bytes"] <= MAX_BYTES,
                    "typed object descriptor bound",
                )
                path, size = entry["path"], entry["bytes"]
                a.require(
                    path not in object_sizes or object_sizes[path] == size,
                    "typed duplicate object size",
                )
                object_sizes[path] = size
    a.require(sum(object_sizes.values()) <= MAX_BYTES, "typed support batch byte bound")
    paths, seen = set(), set()
    image_bytes, image_count = 0, 0
    for bundle in bundles:
        fields(
            bundle,
            "sourceCommit sourceTree requestedHead runId attempt suite case project manifests receipts"
            + (" nativeEnvelopes" if "nativeEnvelopes" in bundle else "")
            + (" nativeReports" if "nativeReports" in bundle else ""),
        )
        a.require(
            all(
                type(bundle[k]) is str and re.fullmatch("[a-f0-9]{40}", bundle[k])
                for k in ("sourceCommit", "sourceTree", "requestedHead")
            ),
            "typed source",
        )
        a.require(
            all(type(bundle[k]) is int and bundle[k] > 0 for k in ("runId", "attempt")), "typed run"
        )
        a.require(
            all(type(bundle[k]) is str for k in ("suite", "case", "project"))
            and producer_title(bundle["suite"], bundle["case"], bundle["project"]),
            "typed producer",
        )
        key = tuple(bundle[k] for k in ("runId", "attempt", "suite", "case"))
        a.require(key not in seen, "duplicate typed bundle")
        seen.add(key)
        a.verify_source(repo, bundle)
        manifests = bundle["manifests"]
        a.require(
            type(manifests) is list
            and (0 if local_context is not None else 1) <= len(manifests) <= 480,
            "typed manifest count",
        )
        frames, manifest_paths = {}, set()
        for entry in manifests:
            fields(entry, "path sha256")
            a.require(
                type(entry["path"]) is str
                and re.fullmatch(
                    (
                        r"runs/[0-9]+-[0-9]+-[0-9]+-[0-9]+\.json"
                        if local_context is None
                        else r"local-manifests/[a-f0-9]{64}\.json"
                    ),
                    entry["path"],
                )
                and entry["path"] not in manifest_paths,
                "typed manifest path",
            )
            manifest_paths.add(entry["path"])
            manifest_root = repo / "evidence/visual" if local_context is None else object_root
            manifest_path = a.safe_path(manifest_root, entry["path"])
            if local_context is not None and not manifest_path.is_file():
                from scripts.python.local_capture_proof import MissingLocalDependency

                raise MissingLocalDependency("missing local capture manifest")
            if local_context is not None:
                a.require(
                    0 < manifest_path.stat().st_size <= MAX_BYTES, "local manifest byte bound"
                )
            raw = manifest_path.read_bytes()
            a.require(
                len(raw) <= MAX_BYTES and a.digest(raw) == entry["sha256"],
                "typed manifest identity",
            )
            manifest = strict(raw)
            profile = "git" if local_context is None else "local-zip"
            a.validate_capture_manifest(manifest, profile=profile)
            a.require(
                entry["path"]
                == (
                    f"runs/{manifest['runId']}-{manifest['attempt']}-{manifest['jobId']}-{manifest['artifactId']}.json"
                    if local_context is None
                    else f"local-manifests/{entry['sha256']}.json"
                ),
                "typed manifest filename identity",
            )
            a.require(
                all(
                    manifest[k] == bundle[k]
                    for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
                ),
                "typed manifest source/run",
            )
            if local_context is not None:
                a.require(
                    all(manifest[k] == bundle[k] for k in ("suite", "case", "project")),
                    "local exact bundle producer",
                )
            matched = False
            for capture in manifest["captures"]:
                member = Path(capture["member"])
                if member.parent.name != bundle["case"]:
                    continue
                matched = True
                if capture["originalOutcome"] != "unknown":
                    a.require(
                        capture["test"]
                        == producer_title(bundle["suite"], bundle["case"], bundle["project"]),
                        "typed native test mismatch",
                    )
                a.require(
                    capture["project"] == bundle["project"]
                    or (local_context is not None and capture["project"] is None),
                    "typed frame project",
                )
                image_bytes += capture["bytes"]
                image_count += 1
                a.require(image_bytes <= 6 * 1024**3 and image_count <= 65536, "typed frame budget")
                image = a.capture_storage_bytes(
                    repo, manifest, capture, profile=profile, local_context=local_context
                )
                a.require(
                    len(image) == capture["bytes"]
                    and a.digest(image) == capture["sha256"]
                    and a.png(image) == capture["dimensions"],
                    "typed frame bytes/dimensions",
                )
                a.require(
                    member.name not in frames or frames[member.name] == image,
                    "ambiguous cross-part frame",
                )
                frames[member.name] = image
            a.require(matched, "unrelated typed manifest")
        if local_context is not None:
            # Bind every original metadata object to the actual original ZIP
            # before common closed-schema and cross-object validation. No archive
            # or unapproved container payload is copied into the repository.
            for group in ("receipts", "nativeEnvelopes", "nativeReports"):
                for entry in bundle.get(group, []):
                    original = local_context.diagnostic_bytes(entry, bundle)
                    source = a.safe_path(object_root, entry["path"])
                    if not source.is_file():
                        from scripts.python.local_capture_proof import MissingLocalDependency

                        raise MissingLocalDependency("missing local diagnostic object")
                    a.require(source.stat().st_size == len(original), "local diagnostic byte bound")
                    a.require(
                        source.read_bytes() == original, "local diagnostic/archive crossbinding"
                    )
        envelopes = load_native_envelopes(
            bundle.get("nativeEnvelopes", []),
            bundle,
            object_root or repo / "evidence/visual/support",
            repo=repo,
            historical_profiles=historical_profiles,
            classifications=classifications,
        )
        paths.update(
            load_native_reports(
                bundle.get("nativeReports", []),
                envelopes,
                bundle,
                object_root or repo / "evidence/visual/support",
            )
        )
        used_envelopes = set()
        receipts = bundle["receipts"]
        a.require(type(receipts) is list and 0 < len(receipts) <= 256, "typed receipt count")
        with tempfile.TemporaryDirectory(prefix="base2-typed-") as temporary:
            case_path = Path(temporary) / bundle["case"]
            case_path.mkdir()
            for name, image in frames.items():
                (case_path / name).write_bytes(image)
            names, loaded = set(), []
            total = 0
            for entry in receipts:
                fields(
                    entry,
                    "path sha256 bytes family schemaVersion artifactId archiveSha256 member archiveChain",
                )
                digest = entry["sha256"]
                a.require(
                    type(digest) is str
                    and re.fullmatch("[a-f0-9]{64}", digest)
                    and entry["path"] == f"objects/{digest}.json",
                    "typed receipt storage",
                )
                a.require(
                    type(entry["artifactId"]) is int
                    and entry["artifactId"] > 0
                    and type(entry["archiveSha256"]) is str
                    and re.fullmatch("[a-f0-9]{64}", entry["archiveSha256"]),
                    "typed original archive identity",
                )
                a.validate_chain(dict(entry, storage=entry["path"]))
                member = Path(entry["member"])
                a.require(
                    member.parent.name == bundle["case"] and member.name not in names,
                    "typed receipt member",
                )
                names.add(member.name)
                raw = bound_bytes(object_root or repo / "evidence/visual/support", entry)
                total += len(raw)
                a.require(total <= MAX_BYTES, "typed bundle receipt budget")
                path = case_path / member.name
                a.require(path.name.endswith(".json") and path.name not in frames, "typed filename")
                path.write_bytes(raw)
                if entry["family"] in {"checkpoint", "media-geometry"}:
                    matches = []
                    for envelope, data in envelopes:
                        try:
                            native_envelope_binding(entry, envelope, data, frames)
                        except ValueError:
                            continue
                        matches.append(envelope)
                    a.require(
                        len(matches) == 1,
                        "source-less diagnostic requires unique native envelope crossbinding",
                    )
                    used_envelopes.add(matches[0]["path"])
                loaded.append((raw, path, entry))
                paths.add(entry["path"])
            # All cross-part originals are materialized before any validator runs.
            # Missing dependencies fail; partial native status remains unmodified.
            for raw, path, entry in loaded:
                validate_receipt(raw, path, entry["family"], entry["schemaVersion"], bundle, repo)
        a.require(
            used_envelopes == {entry["path"] for entry, _ in envelopes}, "unused native envelope"
        )
        paths.update(used_envelopes)
    return paths


def validate_registry(repo, registry, object_root=None):
    try:
        return _validate_registry(repo, registry, object_root)
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as error:
        raise ValueError("invalid typed registry shape") from error


def validate_local_registry(
    repo, registry, object_root, local_context, *, historical_profiles=None
):
    """Read-only closure; never accepted by persistent register/validate_registry."""
    from scripts.python.local_capture_proof import LocalZipContext, MissingLocalDependency

    a.require(type(local_context) is LocalZipContext, "explicit local ZIP context required")
    historical_profiles = {} if historical_profiles is None else historical_profiles
    a.require(
        type(historical_profiles) is dict and len(historical_profiles) <= 480,
        "historical profile selection",
    )
    a.require(
        all(
            type(k) is str
            and re.fullmatch("[a-f0-9]{64}", k)
            and v == "historical-media-packaging-a131afa-bd57b58"
            for k, v in historical_profiles.items()
        ),
        "historical profile selection",
    )
    classifications = {}
    try:
        paths = _validate_registry(
            repo,
            registry,
            object_root,
            local_context=local_context,
            historical_profiles=historical_profiles,
            classifications=classifications,
        )
        a.require(set(classifications) == set(historical_profiles), "unused historical profile")
    except MissingLocalDependency as error:
        return dict(
            profile="local-zip",
            dependencyComplete=False,
            suppliedDependencyClosure=False,
            historicalClassifications=classifications,
            acceptance=False,
            runComplete=False,
            errors=[str(error)],
            paths=[],
        )
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as error:
        raise ValueError("invalid local typed registry shape") from error
    return dict(
        profile="local-zip",
        dependencyComplete=not classifications,
        suppliedDependencyClosure=True,
        historicalClassifications=classifications,
        acceptance=False,
        runComplete=False,
        errors=[],
        paths=sorted(paths),
    )


def register(repo, registry_raw, object_root):
    """Validate closure before writing immutable originals; never edit source catalogs."""
    registry = strict(registry_raw)
    paths = validate_registry(repo, registry, object_root)
    destination = repo / "evidence/visual/support"
    planned = {path: a.safe_path(object_root, path).read_bytes() for path in paths}
    a.require(
        all(a.digest(raw) == Path(name).stem for name, raw in planned.items()),
        "typed source changed during registration",
    )
    planned[f"registries/{a.digest(registry_raw)}.json"] = registry_raw
    # Preflight every identity before any mutation. Repeated import is a no-op.
    for name, raw in planned.items():
        path = a.safe_path(destination, name)
        a.require(not path.exists() or path.read_bytes() == raw, "immutable support collision")
    created = []
    try:
        for name, raw in planned.items():
            path = a.safe_path(destination, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                with path.open("xb") as stream:
                    created.append(path)
                    stream.write(raw)
    except BaseException:
        for path in reversed(created):
            path.unlink()
        raise
    return f"registries/{a.digest(registry_raw)}.json"


def validate_quarantine_registry(repo, registry, object_root=None):
    """Validate identity-only retention of a known contradictory native object.

    Quarantine objects live outside the proof-object namespace. No image closure,
    coverage, native outcome, or acceptance is inferred from their retention.
    """
    from scripts.python import native_archive_evidence as native

    fields(registry, "schemaVersion kind acceptance closure entries")
    a.require(
        type(registry["schemaVersion"]) is int
        and registry["schemaVersion"] == 3
        and registry["kind"] == "quarantined-native-diagnostics"
        and registry["acceptance"] is False
        and registry["closure"] is False,
        "quarantine registry profile",
    )
    entries = registry["entries"]
    a.require(type(entries) is list and 0 < len(entries) <= 32, "quarantine entry bound")
    paths, total = set(), 0
    for entry in entries:
        fields(entry, "sourceCommit sourceTree requestedHead runId attempt object contradictions")
        a.require(
            all(
                type(entry[k]) is str and re.fullmatch("[a-f0-9]{40}", entry[k])
                for k in ("sourceCommit", "sourceTree", "requestedHead")
            )
            and all(type(entry[k]) is int and entry[k] > 0 for k in ("runId", "attempt")),
            "quarantine source/run",
        )
        a.verify_source(repo, entry)
        obj = entry["object"]
        fields(obj, "path sha256 bytes artifactId archiveSha256 member archiveChain")
        a.require(
            type(obj["sha256"]) is str
            and re.fullmatch("[a-f0-9]{64}", obj["sha256"])
            and obj["path"] == f"quarantine/objects/{obj['sha256']}.json"
            and obj["path"] not in paths,
            "quarantine object namespace",
        )
        a.require(
            type(obj["bytes"]) is int and 0 < obj["bytes"] <= native.BUDGET,
            "quarantine object size",
        )
        total += obj["bytes"]
        a.require(total <= MAX_BYTES, "quarantine aggregate bound")
        a.require(
            type(obj["artifactId"]) is int
            and obj["artifactId"] > 0
            and type(obj["archiveSha256"]) is str
            and re.fullmatch("[a-f0-9]{64}", obj["archiveSha256"]),
            "quarantine original archive",
        )
        a.validate_chain(dict(obj, storage=obj["path"]))
        a.require(Path(obj["member"]).name == "inventory.json", "quarantine original family")
        raw = bound_bytes(object_root or repo / "evidence/visual/support", obj)
        result = native.classify_original(raw, "inventory.json", entry)
        a.require(
            result["status"] == "quarantined-invalid-diagnostic"
            and entry["contradictions"] == result["contradictions"],
            "quarantine classification mismatch",
        )
        paths.add(obj["path"])
    return paths


def register_quarantine(repo, registry_raw, object_root):
    """Retain contradictory bytes immutably; never pass them to proof registration."""
    registry = strict(registry_raw)
    paths = validate_quarantine_registry(repo, registry, object_root)
    planned = {path: a.safe_path(object_root, path).read_bytes() for path in paths}
    a.require(
        all(a.digest(raw) == Path(path).stem for path, raw in planned.items()),
        "quarantine source changed during registration",
    )
    name = f"registries/{a.digest(registry_raw)}.json"
    planned[name] = registry_raw
    destination = repo / "evidence/visual/support"
    for path, raw in planned.items():
        target = a.safe_path(destination, path)
        a.require(
            not target.exists() or target.read_bytes() == raw, "immutable quarantine collision"
        )
    created = []
    try:
        for path, raw in planned.items():
            target = a.safe_path(destination, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with target.open("xb") as stream:
                    created.append(target)
                    stream.write(raw)
    except BaseException:
        for target in reversed(created):
            target.unlink()
        raise
    return name


def _load_external_transport(repo, registry, object_root):
    """Retain external transport identity without satisfying native proof gates."""
    from scripts.python import native_archive_evidence as native

    # Every supplied transport remains immutable and content-addressed. The
    # native validator checks each complete ZIP and all exact nested members.
    fields(
        registry,
        "schemaVersion kind acceptance runComplete nativePartClosure provenance inventory members",
    )
    rows = [registry["inventory"], *registry["members"]]
    a.require(len(rows) <= 65537, "external registry member bound")
    archives, paths = {}, set()
    root = object_root or repo / "evidence/visual/support"
    for row in rows:
        sha = row["archiveSha256"]
        a.require(type(sha) is str and re.fullmatch("[a-f0-9]{64}", sha), "external archive digest")
        path = f"external/transport/{sha}.zip"
        source = a.safe_path(root, path)
        a.require(
            source.is_file() and 0 < source.stat().st_size <= 32 * 1024**2,
            "external transport bound",
        )
        if sha not in archives:
            a.require(len(archives) < 512, "external transport count bound")
            a.require(
                sum(len(body) for body in archives.values()) + source.stat().st_size <= 6 * 1024**3,
                "external aggregate transport bound",
            )
            archives[sha] = source.read_bytes()
        paths.add(path)
    return native.validate_external_inventory_transport(repo, registry, archives)


def register_external_inventory(repo, registry_raw, object_root):
    """Data-only registration; no native parts are invented or accepted."""
    registry = strict(registry_raw)
    result = _load_external_transport(repo, registry, object_root)
    planned = {}
    for row in [registry["inventory"], *registry["members"]]:
        body = result["leaves"][row["key"]]
        path = external_leaf_path(row)
        a.require(a.digest(body) == row["chain"][-1]["sha256"], "external leaf changed")
        planned[path] = body
    # New explicit leaf-only retention profile. Original leaf bytes are not
    # rewritten; no raw ZIP, comment, extra field or trailing payload is stored.
    retained = dict(registry, schemaVersion=5, kind="external-inventory-v1-leaves")
    _validate_external_registry(repo, retained, planned.__getitem__)
    import json

    retained_raw = (json.dumps(retained, sort_keys=True, separators=(",", ":")) + "\n").encode()
    name = f"registries/{a.digest(retained_raw)}.json"
    planned[name] = retained_raw
    destination = repo / "evidence/visual/support"
    for path, raw in planned.items():
        target = a.safe_path(destination, path)
        a.require(not target.exists() or target.read_bytes() == raw, "immutable external collision")
    created = []
    try:
        for path, raw in planned.items():
            target = a.safe_path(destination, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with target.open("xb") as stream:
                    created.append(target)
                    stream.write(raw)
    except BaseException:
        for target in reversed(created):
            target.unlink()
        raise
    return name


def external_leaf_path(row):
    sha = row["chain"][-1]["sha256"]
    a.require(type(sha) is str and re.fullmatch("[a-f0-9]{64}", sha), "external leaf digest")
    suffix = (
        ".png"
        if row["key"].endswith(".png")
        else ".md"
        if row["key"] == "reports/stages.md"
        else ".json"
    )
    return f"external/objects/{sha}{suffix}"


def validate_external_registry(repo, registry, object_root=None):
    """Revalidate retained leaves, not unavailable original container bytes.

    Chains are externally verified provenance. They do not become native part
    declarations or a fresh independent replay of the discarded transport ZIPs.
    """
    root = object_root or repo / "evidence/visual/support"

    def read_leaf(path):
        source = a.safe_path(root, path)
        a.require(
            source.is_file() and 0 < source.stat().st_size <= 32 * 1024**2,
            "external retained size",
        )
        return source.read_bytes()

    return _validate_external_registry(repo, registry, read_leaf)


def _validate_external_registry(repo, registry, read_leaf):
    """Validate the complete profile against either planned or retained bytes."""
    from scripts.python import native_archive_evidence as native

    fields(
        registry,
        "schemaVersion kind acceptance runComplete nativePartClosure provenance inventory members",
    )
    a.require(
        type(registry["schemaVersion"]) is int
        and registry["schemaVersion"] == 5
        and registry["kind"] == "external-inventory-v1-leaves"
        and registry["acceptance"] is False
        and registry["runComplete"] is False
        and registry["nativePartClosure"] == "unavailable",
        "external leaf retention profile",
    )
    fields(registry["provenance"], "sourceCommit sourceTree requestedHead runId attempt")
    a.verify_source(repo, registry["provenance"])
    paths, locations = set(), set()
    total = 0

    def resolve(row):
        nonlocal total
        native.validate_external_descriptor(row)
        location = (
            row["artifactId"],
            row["archiveSha256"],
            tuple(x["member"] for x in row["chain"]),
        )
        a.require(location not in locations, "external duplicate retained binding")
        locations.add(location)
        path = external_leaf_path(row)
        body = read_leaf(path)
        a.require(type(body) is bytes and 0 < len(body) <= 32 * 1024**2, "external retained size")
        total += len(body)
        a.require(total <= 6 * 1024**3, "external retained aggregate")
        leaf = row["chain"][-1]
        a.require(
            len(body) == leaf["bytes"] and a.digest(body) == leaf["sha256"],
            "external retained identity",
        )
        paths.add(path)
        return body

    native.validate_external_inventory_contents(registry, resolve)
    return paths
