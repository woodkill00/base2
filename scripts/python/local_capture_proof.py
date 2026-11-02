"""Read-only local ZIP capture proof, distinct from persistent Git transfer.

No ZIP, image, or registry is imported here. Closure is local byte/source identity,
not native test success or technical/visual acceptance. The job index is externally
verified evidence: its trusted digest must be supplied separately by the reviewer.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

from scripts.python import screenshot_archive as a

PROFILE = "local-zip-capture-proof"
MAX_ARCHIVE = 32 * 1024**2


class MissingLocalDependency(ValueError):
    """Validly named required bytes are unavailable; never substitute Git proof."""


def fields(value, names):
    a.require(type(value) is dict and set(value) == set(names.split()), "local proof fields")


def strict(raw):
    from scripts.python.typed_archive_support import strict as parse

    return parse(raw)


class ExternalJobIndex:
    """Reviewer-pinned original jobs index; does not fabricate a new API proof."""

    def __init__(self, job_index_raw, trusted_job_index_sha256):
        a.require(
            type(trusted_job_index_sha256) is str
            and re.fullmatch(r"[a-f0-9]{64}", trusted_job_index_sha256)
            and len(job_index_raw) <= 16 * 1024**2
            and a.digest(job_index_raw) == trusted_job_index_sha256,
            "local trusted job index identity",
        )
        index = strict(job_index_raw)
        a.require(type(index.get("runs")) is list and 0 < len(index["runs"]) <= 512, "local jobs")
        self.job_index_sha256 = trusted_job_index_sha256
        self.jobs = index["runs"]

    def bind_job(self, data):
        matches = [
            row
            for row in self.jobs
            if str(row.get("runId")) == str(data["runId"]) and row.get("attempt") == data["attempt"]
        ]
        a.require(len(matches) == 1, "local unique original job binding")
        row = matches[0]
        a.require(
            type(data["jobId"]) is int
            and data["jobId"] > 0
            and row["jobId"] == data["jobId"]
            and row["requestedHead"] == data["requestedHead"]
            and data["jobIndexSha256"] == self.job_index_sha256
            and data["jobReadSha256"] == row["originalReadSHA256"],
            "local source/run/job binding",
        )
        a.require(re.fullmatch(r"[a-f0-9]{64}", data["jobReadSha256"]), "local job read digest")


class LocalZipContext(ExternalJobIndex):
    def __init__(
        self,
        root,
        job_index_raw,
        trusted_job_index_sha256,
        artifact_index_raw,
        trusted_artifact_index_sha256,
    ):
        super().__init__(job_index_raw, trusted_job_index_sha256)
        self.root = Path(root)
        a.require(
            type(trusted_artifact_index_sha256) is str
            and re.fullmatch(r"[a-f0-9]{64}", trusted_artifact_index_sha256)
            and len(artifact_index_raw) <= 16 * 1024**2
            and a.digest(artifact_index_raw) == trusted_artifact_index_sha256,
            "local trusted artifact index identity",
        )
        artifact_index = strict(artifact_index_raw)
        fields(artifact_index, "artifacts")
        a.require(
            type(artifact_index["artifacts"]) is list
            and 0 < len(artifact_index["artifacts"]) <= 4096,
            "local artifact index",
        )
        self.artifacts = artifact_index["artifacts"]
        self.used_archives = {}
        self.bound_archive_sizes = {}

    def bind_artifact(self, identity, entry):
        matches = [row for row in self.artifacts if row.get("artifactId") == entry["artifactId"]]
        a.require(len(matches) == 1, "local unique artifact binding")
        row = matches[0]
        fields(
            row,
            "artifactId archiveSha256 bytes sourceCommit sourceTree requestedHead runId attempt jobId",
        )
        a.require(
            all(
                row[k] == identity[k]
                for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
            )
            and row["archiveSha256"] == entry["archiveSha256"],
            "local original artifact source/run binding",
        )
        jobs = [
            job
            for job in self.jobs
            if str(job.get("runId")) == str(identity["runId"])
            and job.get("attempt") == identity["attempt"]
        ]
        a.require(len(jobs) == 1 and row["jobId"] == jobs[0]["jobId"], "local artifact/job binding")
        a.require(
            type(row["bytes"]) is int and 0 < row["bytes"] <= MAX_ARCHIVE, "local artifact size"
        )
        self.bound_archive_sizes[row["archiveSha256"]] = row["bytes"]

    def member_bytes(self, archive_sha, chain):
        a.require(
            type(archive_sha) is str and re.fullmatch(r"[a-f0-9]{64}", archive_sha),
            "local archive hash",
        )
        a.require(type(chain) is list and 1 <= len(chain) <= 3, "local chain bound")
        path = a.safe_path(self.root, f"transport/{archive_sha}.zip")
        if not path.is_file():
            raise MissingLocalDependency("missing local original archive")
        a.require(0 < path.stat().st_size <= MAX_ARCHIVE, "local archive byte bound")
        if archive_sha not in self.used_archives:
            a.require(len(self.used_archives) < 512, "local archive count")
            self.used_archives[archive_sha] = path.stat().st_size
            a.require(
                sum(self.used_archives.values()) <= 6 * 1024**3, "local aggregate archive bound"
            )
        body = path.read_bytes()
        a.require(
            a.digest(body) == archive_sha
            and len(body) == self.bound_archive_sizes.get(archive_sha),
            "local original archive changed/unbound",
        )
        for link in chain:
            fields(link, "member sha256 hashBasis")
            name = link["member"]
            a.require(type(name) is str and 0 < len(name) <= 512, "local member length")
            a.safe_path(Path("."), name)
            a.require(
                str(Path(name)) == name and not any(ord(c) < 32 for c in name),
                "local canonical member",
            )
            a.require(
                (
                    link["sha256"] is None
                    and link["hashBasis"] == "unavailable-in-retained-inventory"
                )
                or (
                    type(link["sha256"]) is str
                    and re.fullmatch(r"[a-f0-9]{64}", link["sha256"])
                    and link["hashBasis"] == "externally-verified-original-member"
                ),
                "local member hash basis",
            )
            try:
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    infos = archive.infolist()
                    names = [i.filename for i in infos]
                    a.require(
                        len(names) <= 65536 and len(names) == len(set(names)),
                        "local duplicate members",
                    )
                    a.require(
                        sum(i.file_size for i in infos) <= MAX_ARCHIVE, "local expanded byte bound"
                    )
                    for info in infos:
                        a.safe_path(Path("."), info.filename)
                        a.require(
                            not info.flag_bits & 1
                            and (info.external_attr >> 16) & 0o170000 != 0o120000,
                            "local unsafe ZIP",
                        )
                    if name not in names:
                        raise MissingLocalDependency("missing local original member")
                    info = archive.getinfo(name)
                    a.require(
                        not info.is_dir() and 0 < info.file_size <= MAX_ARCHIVE,
                        "local member bound",
                    )
                    body = archive.read(info)
            except zipfile.BadZipFile as error:
                raise ValueError("local invalid original ZIP") from error
            if link["sha256"] is not None:
                a.require(a.digest(body) == link["sha256"], "local member digest")
        return body

    def diagnostic_bytes(self, entry, identity):
        self.bind_artifact(identity, entry)
        body = self.member_bytes(entry["archiveSha256"], entry["archiveChain"])
        a.require(
            len(body) == entry["bytes"] and a.digest(body) == entry["sha256"],
            "local diagnostic identity",
        )
        return body


def validate_manifest(data):
    """Closed local profile; no transfer fields, review grants, or inferred passes."""
    from scripts.python.typed_archive_support import producer_title

    fields(
        data,
        "schemaVersion kind repository sourceCommit sourceTree requestedHead runId attempt jobId artifactId archiveSha256 jobIndexSha256 jobReadSha256 suite case project fixtureScope originalOutcome captures acceptance runComplete",
    )
    a.require(
        type(data["schemaVersion"]) is int
        and data["schemaVersion"] == 3
        and data["kind"] == PROFILE,
        "local capture profile",
    )
    a.require(
        data["repository"] == "woodkill00/base2"
        and data["fixtureScope"] == "synthetic-project-tests",
        "local fixture/repository",
    )
    a.require(
        data["acceptance"] is False
        and data["runComplete"] is False
        and data["originalOutcome"] == "unknown",
        "local proof cannot grant outcome",
    )
    a.require(
        all(
            type(data[k]) is str and re.fullmatch(r"[a-f0-9]{40}", data[k])
            for k in ("sourceCommit", "sourceTree", "requestedHead")
        ),
        "local source",
    )
    a.require(
        all(
            type(data[k]) is int and data[k] > 0
            for k in ("runId", "attempt", "jobId", "artifactId")
        ),
        "local native identity",
    )
    a.require(
        all(
            type(data[k]) is str and re.fullmatch(r"[a-f0-9]{64}", data[k])
            for k in ("archiveSha256", "jobIndexSha256", "jobReadSha256")
        ),
        "local digest",
    )
    a.require(
        all(type(data[k]) is str for k in ("suite", "case", "project"))
        and producer_title(data["suite"], data["case"], data["project"]),
        "local exact producer",
    )
    a.require(
        type(data["captures"]) is list and 0 < len(data["captures"]) <= 256, "local capture count"
    )
    seen = set()
    for capture in data["captures"]:
        fields(
            capture,
            "member sha256 bytes dimensions project test originalOutcome storage archiveChain",
        )
        a.require(
            type(capture["member"]) is str
            and Path(capture["member"]).parent.name == data["case"]
            and capture["member"] not in seen,
            "local case/member",
        )
        seen.add(capture["member"])
        a.require(
            type(capture["sha256"]) is str and re.fullmatch(r"[a-f0-9]{64}", capture["sha256"]),
            "local PNG hash",
        )
        a.require(
            capture["storage"] == f"local-zip:{data['archiveSha256']}:{capture['sha256']}.png",
            "local storage profile",
        )
        a.validate_chain(capture)
        a.require(
            capture["archiveChain"][-1]["member"] == capture["member"]
            and capture["archiveChain"][-1]["sha256"] == capture["sha256"],
            "local leaf binding",
        )
        a.require(
            capture["project"] in (None, data["project"])
            and capture["test"]
            in (None, producer_title(data["suite"], data["case"], data["project"])),
            "local producer binding",
        )
        a.require(capture["originalOutcome"] == "unknown", "local native outcome not inferred")
        a.require(
            type(capture["bytes"]) is int and 0 < capture["bytes"] <= a.MAX_BYTES,
            "local image bound",
        )
        a.require(
            type(capture["dimensions"]) is list
            and len(capture["dimensions"]) == 2
            and all(type(n) is int and 0 < n <= 32768 for n in capture["dimensions"]),
            "local image dimensions",
        )
    a.require(
        sum(c["bytes"] for c in data["captures"]) <= a.MAX_BYTES, "local manifest byte budget"
    )


def capture_bytes(repo, data, capture, context):
    validate_manifest(data)
    a.verify_source(repo, data)
    context.bind_job(data)
    context.bind_artifact(data, data)
    a.require(capture in data["captures"], "local capture membership")
    raw = context.member_bytes(data["archiveSha256"], capture["archiveChain"])
    a.require(
        len(raw) == capture["bytes"]
        and a.digest(raw) == capture["sha256"]
        and a.png(raw) == capture["dimensions"],
        "local PNG identity/decode",
    )
    return raw


def plan_capture_manifests(bundle_plan, context, *, binding=None):
    """Translate supplied backend-neutral capture descriptors, without claiming validation.

    Native envelopes/reports must still be selected and crossbound by the typed
    registry caller. Missing original archives remain missing, not manufactured.
    """
    from collections import defaultdict

    if bundle_plan["captureDescriptors"] == []:
        # Metadata-only/skipped historical receipts still require closed typed
        # receipt validation and an explicit registered bundle producer.
        return []
    projects = bundle_plan["projectCandidates"]
    if binding is not None:
        import json

        a.require(
            type(binding) is ValidatedPlanBinding
            and binding.plan_sha == a.digest(json.dumps(bundle_plan, sort_keys=True).encode()),
            "validated binding belongs to unchanged plan",
        )
        a.require(projects in ([], [binding.project]), "planned explicit project conflict")
        projects = [binding.project]
    a.require(type(projects) is list and len(projects) == 1, "local unambiguous planned project")
    identity = {
        k: bundle_plan[k]
        for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt", "jobId")
    }
    jobs = [
        row
        for row in context.jobs
        if str(row.get("runId")) == str(identity["runId"])
        and row.get("attempt") == identity["attempt"]
    ]
    a.require(len(jobs) == 1, "local planned job binding")
    groups = defaultdict(list)
    for descriptor in bundle_plan["captureDescriptors"]:
        a.require(str(descriptor["runId"]) == str(identity["runId"]), "local planned capture run")
        # The inspected plans explicitly have no per-test outcome binding. Do
        # not convert job conclusion or filename classification into test status.
        a.require(
            descriptor["nativeOutcome"] is None
            and (
                descriptor["nativeTestBindingStatus"] == "unknown-not-inferred-from-filename"
                or (
                    descriptor["nativeTestBindingStatus"] == "exact-project-title"
                    and binding is not None
                    and descriptor["project"] == binding.project
                    and descriptor["test"] == binding.title
                )
            ),
            "local unsupported planned outcome binding",
        )
        chain = []
        for index, link in enumerate(descriptor["archiveMemberChain"]):
            last = index == len(descriptor["archiveMemberChain"]) - 1
            digest = descriptor["sha256"] if last else link.get("sha256")
            chain.append(
                dict(
                    member=link["member"],
                    sha256=digest,
                    hashBasis="externally-verified-original-member"
                    if digest
                    else "unavailable-in-retained-inventory",
                )
            )
        archive_sha = descriptor["artifactZipSha256"]
        groups[(descriptor["artifactId"], archive_sha)].append(
            dict(
                member=chain[-1]["member"],
                sha256=descriptor["sha256"],
                bytes=descriptor["sizeBytes"],
                dimensions=[descriptor["pixels"]["width"], descriptor["pixels"]["height"]],
                project=descriptor["project"],
                test=descriptor["test"],
                originalOutcome="unknown",
                storage=f"local-zip:{archive_sha}:{descriptor['sha256']}.png",
                archiveChain=chain,
            )
        )
    planned = []
    for (artifact_id, archive_sha), captures in sorted(groups.items()):
        manifest = dict(
            identity,
            schemaVersion=3,
            kind=PROFILE,
            repository="woodkill00/base2",
            artifactId=artifact_id,
            archiveSha256=archive_sha,
            jobIndexSha256=context.job_index_sha256,
            jobReadSha256=jobs[0]["originalReadSHA256"],
            suite=bundle_plan["suite"],
            case=bundle_plan["case"],
            project=projects[0],
            fixtureScope="synthetic-project-tests",
            originalOutcome="unknown",
            captures=captures,
            acceptance=False,
            runComplete=False,
        )
        validate_manifest(manifest)
        context.bind_job(manifest)
        planned.append(manifest)
    return planned


class ValidatedPlanBinding:
    """Ephemeral source-backed identity, never an execution outcome or stored plan edit."""

    def __init__(self, plan_sha, project, title, receipts):
        self.plan_sha = plan_sha
        self.project = project
        self.title = title
        self.receipts = receipts


def derive_plan_binding(
    repo,
    plan,
    context,
    *,
    native_entries=(),
    native_reports=(),
    object_root=None,
    historical_profiles=None,
    dependency_descriptors=(),
):
    """Validate original receipt/frame dependencies before deriving explicit fields.

    Source-less diagnostics additionally require already validated native envelopes;
    their identity crossbinding is checked again here. No filename inference.
    """
    import json
    import tempfile

    from scripts.python import typed_archive_support as typed

    a.require(type(context) is LocalZipContext, "original ZIP binding context")
    _validate_plan_producer_path(plan)
    _preflight_plan_resources(plan, dependency_descriptors, native_entries, native_reports)
    a.verify_source(repo, plan)
    envelopes = []
    if native_entries:
        a.require(object_root is not None, "native original object root")
        for entry in (*native_entries, *native_reports):
            raw = context.diagnostic_bytes(entry, plan)
            a.require(
                typed.bound_bytes(object_root, entry) == raw, "native original transport binding"
            )
        classifications = {}
        envelopes = typed.load_native_envelopes(
            list(native_entries),
            plan,
            object_root,
            repo=repo,
            historical_profiles=historical_profiles,
            classifications=classifications,
        )
        a.require(
            set(classifications) == set(historical_profiles or {}), "unused historical profile"
        )
        typed.load_native_reports(list(native_reports), envelopes, plan, object_root)
    else:
        a.require(not native_reports and not historical_profiles, "missing native envelope")
    frames = {}
    # Original transport/source/job verification is independent of native title.
    for capture in plan["captureDescriptors"]:
        a.require(capture["nativeOutcome"] is None, "planned outcome must remain unknown")
        entry = _plan_original_entry(capture)
        raw = context.diagnostic_bytes(entry, plan)
        a.require(
            a.png(raw) == [capture["pixels"]["width"], capture["pixels"]["height"]],
            "planned PNG dimensions",
        )
        name = Path(entry["member"]).name
        a.require(Path(entry["member"]).parent.name == plan["case"], "planned original case")
        a.require(name not in frames or frames[name] == raw, "ambiguous planned PNG")
        frames[name] = raw
    identities, proofs = set(), []
    with tempfile.TemporaryDirectory(prefix="base2-plan-binding-") as temporary:
        temporary_root = Path(temporary).resolve(strict=True)
        case = temporary_root / plan["case"]
        a.require(case.resolve().parent == temporary_root, "planned case containment")
        case.mkdir()
        for name, raw in frames.items():
            (case / name).write_bytes(raw)
        staged = []
        names = set(frames)
        a.require(
            type(dependency_descriptors) in (tuple, list)
            and len(plan["receiptDescriptors"]) + len(dependency_descriptors) <= 256,
            "planned receipt dependency bound",
        )
        for descriptor in [*plan["receiptDescriptors"], *dependency_descriptors]:
            locations = [
                x for x in descriptor["originalLocations"] if str(x["runId"]) == str(plan["runId"])
            ]
            a.require(len(locations) == 1, "unique planned receipt location")
            entry = _plan_original_entry(locations[0])
            a.require(
                entry["sha256"] == descriptor["sha256"] and entry["bytes"] == descriptor["bytes"],
                "planned receipt descriptor",
            )
            raw = context.diagnostic_bytes(entry, plan)
            path = case / Path(entry["member"]).name
            a.require(Path(entry["member"]).parent.name == plan["case"], "original receipt case")
            a.require(
                path.name not in names and path.resolve().parent == case.resolve(),
                "duplicate or unsafe receipt dependency",
            )
            names.add(path.name)
            path.write_bytes(raw)
            staged.append((descriptor, entry, raw, path))
        project, title = _consistent_receipt_identity(
            plan, [strict(raw) for _, _, raw, _ in staged]
        )
        identities.add((project, title))
        bundle = dict(plan, project=project)
        for descriptor, entry, raw, path in staged:
            if descriptor["family"] == "sequence":
                state = strict(raw)["binding"]["state"]
                a.require(
                    type(state) is str and re.fullmatch(r"[a-z0-9-]+", state),
                    "planned sequence state",
                )
                if not (case / f"continuous-{state}.json").is_file():
                    raise MissingLocalDependency("missing exact continuous sequence dependency")
            typed.validate_receipt(
                raw, path, descriptor["family"], descriptor["schemaVersion"], bundle, repo
            )
            if descriptor["family"] in {"media-geometry", "checkpoint"}:
                matches = 0
                for envelope, native_data in envelopes:
                    try:
                        typed.native_envelope_binding(
                            dict(entry, family=descriptor["family"]), envelope, native_data, frames
                        )
                    except ValueError:
                        continue
                    matches += 1
                a.require(matches == 1, "explicit project requires native envelope closure")
            proofs.append(descriptor["sha256"])
    a.require(len(identities) == 1, "unique explicit receipt identity")
    project, title = next(iter(identities))
    candidates = plan["projectCandidates"]
    a.require(candidates in ([], [project]), "explicit project conflicts with original plan")
    return ValidatedPlanBinding(
        a.digest(json.dumps(plan, sort_keys=True).encode()), project, title, proofs
    )


def _plan_original_entry(descriptor):
    chain = []
    for index, link in enumerate(descriptor["archiveMemberChain"]):
        digest = (
            descriptor["sha256"]
            if index == len(descriptor["archiveMemberChain"]) - 1
            else link.get("sha256")
        )
        chain.append(
            dict(
                member=link["member"],
                sha256=digest,
                hashBasis="externally-verified-original-member"
                if digest
                else "unavailable-in-retained-inventory",
            )
        )
    a.require(bool(chain), "planned original chain")
    return dict(
        artifactId=descriptor["artifactId"],
        archiveSha256=descriptor["artifactZipSha256"],
        member=chain[-1]["member"],
        archiveChain=chain,
        sha256=descriptor["sha256"],
        bytes=descriptor["sizeBytes"],
    )


def _validate_plan_producer_path(plan):
    """Validate registration before filesystem access; never derive a binding here."""
    from scripts.python import typed_archive_support as typed

    a.require(type(plan) is dict, "planned producer object")
    suite, case, candidates = plan.get("suite"), plan.get("case"), plan.get("projectCandidates")
    a.require(
        type(suite) is str
        and suite in {"workspace", "media", "operations", "volcano", "settings", "journeys"},
        "planned producer suite",
    )
    a.require(
        type(case) is str
        and 0 < len(case) <= 300
        and re.fullmatch(r"[a-zA-Z0-9_-]+", case) is not None
        and Path(case).parts == (case,)
        and not Path(case).is_absolute(),
        "planned canonical producer case",
    )
    a.require(
        type(candidates) is list
        and len(candidates) <= 1
        and all(type(p) is str and p for p in candidates),
        "planned project candidates",
    )
    # This finite probe only establishes that the case is registered. Its result
    # must never fill absent projectCandidates or become receipt identity proof.
    projects = [
        "chromium",
        "firefox",
        "webkit",
        "firefox-desktop",
        "webkit-desktop",
        "webkit-mobile",
    ]
    projects += [
        "chromium-" + suffix
        for suffix in (
            "compact",
            "phone-dpr3",
            "landscape-touch",
            "tablet",
            "desktop",
            "ultrawide",
            "large-text",
            "400-zoom",
            "400-percent-reflow",
            "light",
            "high-contrast",
            "high-contrast-light",
            "german",
            "rtl",
            "reduced-motion",
        )
    ]
    a.require(
        any(typed.producer_title(suite, case, project) for project in (candidates or projects)),
        "planned registered producer",
    )


def _preflight_plan_resources(plan, dependencies, native_entries, native_reports):
    from scripts.python.typed_archive_support import MAX_BYTES

    captures = plan.get("captureDescriptors")
    receipts = plan.get("receiptDescriptors")
    a.require(type(captures) is list and len(captures) <= 65536, "planned frame count")
    a.require(
        type(receipts) is list
        and type(dependencies) in (list, tuple)
        and len(receipts) + len(dependencies) <= 256,
        "planned receipt count",
    )
    a.require(
        type(native_entries) in (list, tuple)
        and len(native_entries) <= 480
        and type(native_reports) in (list, tuple)
        and len(native_reports) <= 4,
        "planned native count",
    )
    frame_bytes = 0
    for entry in captures:
        a.require(
            type(entry) is dict
            and type(entry.get("sizeBytes")) is int
            and 0 < entry["sizeBytes"] <= MAX_ARCHIVE,
            "planned frame byte bound",
        )
        frame_bytes += entry["sizeBytes"]
    a.require(frame_bytes <= 6 * 1024**3, "planned aggregate frame bytes")
    sizes = {}
    for entry in [*receipts, *dependencies, *native_entries, *native_reports]:
        a.require(
            type(entry) is dict
            and type(entry.get("bytes")) is int
            and 0 < entry["bytes"] <= MAX_BYTES
            and type(entry.get("sha256")) is str
            and re.fullmatch("[a-f0-9]{64}", entry["sha256"]),
            "planned metadata byte bound",
        )
        digest, size = entry["sha256"], entry["bytes"]
        a.require(digest not in sizes or sizes[digest] == size, "planned metadata size conflict")
        sizes[digest] = size
    a.require(sum(sizes.values()) <= MAX_BYTES, "planned aggregate metadata bytes")


def _consistent_receipt_identity(plan, originals):
    """Partial fields constrain identity; they never supply an absent title."""
    from scripts.python import typed_archive_support as typed

    complete, projects, titles = set(), set(), set()
    for data in originals:
        nested = data.get("binding", {})
        a.require(type(nested) is dict, "original identity binding shape")
        ps = {v for v in (data.get("project"), nested.get("project")) if v is not None}
        ts = {v for v in (data.get("test"), nested.get("test")) if v is not None}
        a.require(
            len(ps) <= 1 and len(ts) <= 1 and all(type(v) is str and v for v in ps | ts),
            "conflicting original identity fields",
        )
        projects.update(ps)
        titles.update(ts)
        if ps and ts:
            complete.add((next(iter(ps)), next(iter(ts))))
    a.require(len(complete) == 1, "unique explicit receipt identity")
    project, title = next(iter(complete))
    a.require(projects == {project} and titles == {title}, "conflicting partial receipt identity")
    a.require(
        title == typed.producer_title(plan["suite"], plan["case"], project),
        "explicit original registered title",
    )
    return project, title


def select_plan_route(plan):
    """Bounded applicability decision, never a fallback after validation failure."""
    _validate_plan_producer_path(plan)
    _preflight_plan_resources(plan, (), (), ())
    statuses = set()
    for capture in plan["captureDescriptors"]:
        a.require(capture.get("nativeOutcome") is None, "planned outcome must remain unknown")
        status = capture.get("nativeTestBindingStatus")
        a.require(
            status in {"unknown-not-inferred-from-filename", "exact-project-title"},
            "unsupported planned identity status",
        )
        statuses.add(status)
    if len(plan["projectCandidates"]) == 1 and "exact-project-title" not in statuses:
        return "existing-manifest"
    return "derive-explicit-originals"


def prepare_plan_manifests(repo, plan, context, **derivation_inputs):
    """Choose once; downstream validators remain mandatory and errors propagate."""
    route = select_plan_route(plan)
    if route == "existing-manifest":
        return plan_capture_manifests(plan, context)
    binding = derive_plan_binding(repo, plan, context, **derivation_inputs)
    return plan_capture_manifests(plan, context, binding=binding)
