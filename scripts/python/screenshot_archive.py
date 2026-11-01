"""Import explicitly inventoried synthetic native PNGs; never write test baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

HEX = re.compile(r"[0-9a-f]{64}")
SHA = re.compile(r"[0-9a-f]{40}")
MAX_BYTES = 30 * 1024 * 1024


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def safe_path(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    require(
        bool(parts.parts)
        and not parts.is_absolute()
        and ".." not in parts.parts
        and "\\" not in relative,
        "unsafe path",
    )
    target = root / relative
    require(not any(p.is_symlink() for p in (target, *target.parents)), "symlink rejected")
    return target


def png(raw: bytes) -> list[int]:
    require(len(raw) >= 33 and raw[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "invalid PNG")
    width, height = struct.unpack(">II", raw[16:24])
    require(
        0 < width <= 32768 and 0 < height <= 32768 and width * height <= 32_000_000,
        "invalid dimensions or decoded pixel budget exceeded",
    )
    # Decode and verify the entire file, including chunk CRCs, without re-encoding.
    import io

    from PIL import Image

    with Image.open(io.BytesIO(raw)) as image:
        require(
            image.format == "PNG" and not getattr(image, "is_animated", False), "invalid PNG type"
        )
        image.verify()
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
    return [width, height]


def storage_bytes(repo: Path, storage: str) -> bytes:
    if storage.startswith("git:"):
        _, commit, path = storage.split(":", 2)
        require(
            bool(SHA.fullmatch(commit))
            and path.startswith("react-app/e2e/")
            and "-snapshots/" in path
            and path.endswith(".png"),
            "invalid baseline reference",
        )
        safe_path(repo, path)
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=repo, check=True, timeout=15
        )
        return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=repo, timeout=15)
    return safe_path(repo / "evidence/visual", storage).read_bytes()


def validate_manifest(data: dict) -> None:
    require(
        set(data) - {"transfer"}
        == {
            "schemaVersion",
            "repository",
            "sourceCommit",
            "sourceTree",
            "requestedHead",
            "runId",
            "attempt",
            "jobId",
            "artifactId",
            "archiveSha256",
            "fixtureScope",
            "originalOutcome",
            "captures",
            "technicalReview",
            "laterValidation",
        },
        "unexpected manifest fields",
    )
    require(
        data["schemaVersion"] == 1 and data["repository"] == "woodkill00/base2",
        "wrong repository/schema",
    )
    require(
        all(
            isinstance(data[k], str) and SHA.fullmatch(data[k])
            for k in ("sourceCommit", "sourceTree", "requestedHead")
        ),
        "invalid source identity",
    )
    require(
        all(
            type(data[k]) is int and data[k] > 0
            for k in ("runId", "attempt", "jobId", "artifactId")
        ),
        "invalid native identity",
    )
    require(bool(HEX.fullmatch(data["archiveSha256"])), "invalid archive hash")
    require(data["fixtureScope"] == "synthetic-project-tests", "unapproved fixture scope")
    require(
        data["originalOutcome"] in {"passed", "failed", "timedOut", "interrupted"},
        "invalid outcome",
    )
    require(
        data["technicalReview"] == "pending" and data["laterValidation"] == "pending",
        "imports cannot grant review or validation",
    )
    require(
        isinstance(data["captures"], list) and 0 < len(data["captures"]) <= 256,
        "empty/oversized inventory",
    )
    members = set()
    for c in data["captures"]:
        require(
            set(c)
            == {
                "member",
                "sha256",
                "bytes",
                "dimensions",
                "test",
                "project",
                "viewport",
                "role",
                "originalOutcome",
                "storage",
            },
            "unexpected capture fields",
        )
        safe_path(Path("."), c["member"])
        require(
            c["member"].endswith(".png") and c["member"] not in members, "duplicate/non-PNG member"
        )
        members.add(c["member"])
        require(
            bool(HEX.fullmatch(c["sha256"]))
            and type(c["bytes"]) is int
            and 0 < c["bytes"] <= MAX_BYTES,
            "invalid capture hash/size",
        )
        require(c["role"] in {"actual", "expected", "diff", "current", "failure"}, "invalid role")
        require(
            c["originalOutcome"] in {"passed", "failed", "timedOut", "interrupted"},
            "invalid capture outcome",
        )
        for key in ("test", "project"):
            require(
                isinstance(c[key], str)
                and 0 < len(c[key]) <= 300
                and not any(x in c[key] for x in ("://", "\n", "\r")),
                "invalid test identity",
            )
        for key in ("viewport", "dimensions"):
            require(
                isinstance(c[key], list)
                and len(c[key]) == 2
                and all(type(n) is int and 0 < n <= 32768 for n in c[key]),
                "invalid dimensions",
            )
        require(
            c["storage"] == f"objects/{c['sha256']}.png"
            or re.fullmatch(
                r"git:[0-9a-f]{40}:react-app/e2e/[^:]+-snapshots/[^:]+\.png", c["storage"]
            )
            is not None,
            "invalid object path",
        )
    require(sum(c["bytes"] for c in data["captures"]) <= MAX_BYTES, "inventory exceeds size limit")

    if "transfer" in data:
        transfer = data["transfer"]
        require(
            set(transfer)
            == {"commit", "tree", "originalArchiveVerification", "localVerification", "blobs"},
            "unexpected transfer fields",
        )
        require(
            all(
                isinstance(transfer[k], str) and SHA.fullmatch(transfer[k])
                for k in ("commit", "tree")
            ),
            "invalid transfer identity",
        )
        require(
            transfer["originalArchiveVerification"] == "externally-verified-zip-and-members"
            and transfer["localVerification"] == "git-blob-sha256-size-dimensions-full-decode",
            "invalid transfer verification scope",
        )
        require(
            set(transfer["blobs"]) == {c["sha256"] for c in data["captures"]}
            and all(
                isinstance(blob, str) and SHA.fullmatch(blob) for blob in transfer["blobs"].values()
            ),
            "invalid transfer blob inventory",
        )


def verify_source(repo: Path, data: dict) -> None:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=repo, text=True, timeout=15).strip()

    proof = safe_path(repo / "evidence/visual", f"sources/{data['sourceCommit']}.commit")
    if proof.exists():
        # Preserve the actual Git commit object, not a rewritten pass/source receipt.
        raw = proof.read_bytes()
        require(len(raw) <= 65536, "oversized source proof")
        identity = hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        require(identity == data["sourceCommit"], "source proof identity mismatch")
        headers = raw.split(b"\n\n", 1)[0].splitlines()
        trees = [line[5:].decode("ascii") for line in headers if line.startswith(b"tree ")]
        parents = [line[7:].decode("ascii") for line in headers if line.startswith(b"parent ")]
        require(trees == [data["sourceTree"]], "source proof tree mismatch")
        require(
            data["requestedHead"] in parents or data["requestedHead"] == identity,
            "source proof does not bind requested head",
        )
        # Only tree-equivalent merge sources can use this retained proof path.
        require(
            git("rev-parse", data["requestedHead"] + "^{tree}") == data["sourceTree"],
            "source proof is not equivalent to retained head",
        )
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", data["requestedHead"], "HEAD"],
            cwd=repo,
            check=True,
            timeout=15,
        )
        return
    require(
        git("rev-parse", data["sourceCommit"] + "^{tree}") == data["sourceTree"],
        "source tree mismatch",
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", data["requestedHead"], data["sourceCommit"]],
        cwd=repo,
        check=True,
        timeout=15,
    )


def import_archive(repo: Path, archive: Path, data: dict) -> Path:
    validate_manifest(data)
    require("transfer" not in data, "ZIP import cannot claim Git transfer verification")
    verify_source(repo, data)
    require(
        not archive.is_symlink() and archive.stat().st_size <= 32 * 1024 * 1024,
        "unsafe/oversized ZIP",
    )
    require(digest(archive.read_bytes()) == data["archiveSha256"], "archive hash mismatch")
    destination = repo / "evidence/visual"
    name = f"runs/{data['runId']}-{data['attempt']}-{data['jobId']}-{data['artifactId']}.json"
    manifest = safe_path(destination, name)
    raw_manifest = canonical(data)
    require(
        not manifest.exists() or manifest.read_bytes() == raw_manifest,
        "immutable run manifest conflict",
    )
    payloads = {}
    with zipfile.ZipFile(archive) as z:
        require(len(z.namelist()) == len(set(z.namelist())), "duplicate ZIP entries")
        for c in data["captures"]:
            info = z.getinfo(c["member"])
            require(
                info.file_size == c["bytes"] and (info.external_attr >> 16) & 0o170000 != 0o120000,
                "unsafe ZIP member",
            )
            raw = z.read(info)
            require(
                digest(raw) == c["sha256"] and png(raw) == c["dimensions"],
                "capture integrity mismatch",
            )
            if c["storage"].startswith("git:"):
                require(storage_bytes(repo, c["storage"]) == raw, "baseline reference mismatch")
            else:
                target = safe_path(destination, c["storage"])
                require(
                    not target.exists() or target.read_bytes() == raw, "object integrity conflict"
                )
                payloads[target] = raw
    # All inputs pass before writes. Existing objects and manifests are never overwritten.
    for target, raw in payloads.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(raw)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if not manifest.exists():
        with manifest.open("xb") as stream:
            stream.write(raw_manifest)
    return manifest


def import_git_transfer(repo: Path, data: dict) -> Path:
    """Verify local Git-delivered PNGs; original ZIP verification remains external."""
    validate_manifest(data)
    require("transfer" in data, "explicit Git transfer provenance required")
    verify_source(repo, data)
    transfer = data["transfer"]
    commit = transfer["commit"]
    tree = subprocess.check_output(
        ["git", "rev-parse", commit + "^{tree}"], cwd=repo, text=True, timeout=15
    ).strip()
    require(tree == transfer["tree"], "transfer tree mismatch")
    root = repo / "evidence/visual"
    manifest = safe_path(
        root, f"runs/{data['runId']}-{data['attempt']}-{data['jobId']}-{data['artifactId']}.json"
    )
    raw_manifest = canonical(data)
    require(
        not manifest.exists() or manifest.read_bytes() == raw_manifest,
        "immutable run manifest conflict",
    )
    payloads = {}
    for c in data["captures"]:
        path = f"evidence/visual/objects/{c['sha256']}.png"
        entry = subprocess.check_output(
            ["git", "ls-tree", commit, "--", path], cwd=repo, text=True, timeout=15
        ).strip()
        require(
            entry == f"100644 blob {transfer['blobs'][c['sha256']]}\t{path}",
            "transfer path/blob mismatch",
        )
        blob = transfer["blobs"][c["sha256"]]
        size = subprocess.check_output(
            ["git", "cat-file", "-s", blob], cwd=repo, text=True, timeout=15
        ).strip()
        require(int(size) == c["bytes"], "transfer size mismatch")
        raw = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=repo, timeout=15)
        require(
            digest(raw) == c["sha256"] and png(raw) == c["dimensions"],
            "transfer PNG integrity mismatch",
        )
        if c["storage"].startswith("git:"):
            require(storage_bytes(repo, c["storage"]) == raw, "baseline reference mismatch")
        else:
            target = safe_path(root, c["storage"])
            require(not target.exists() or target.read_bytes() == raw, "object integrity conflict")
            payloads[target] = raw
    for target, raw in payloads.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(raw)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if not manifest.exists():
        with manifest.open("xb") as stream:
            stream.write(raw_manifest)
    return manifest


def validate_archive(repo: Path) -> int:
    root = repo / "evidence/visual"
    count = 0
    for manifest in sorted((root / "runs").glob("*.json")):
        safe_path(root, str(manifest.relative_to(root)))
        data = json.loads(manifest.read_text())
        validate_manifest(data)
        verify_source(repo, data)
        require(
            manifest.name
            == f"{data['runId']}-{data['attempt']}-{data['jobId']}-{data['artifactId']}.json",
            "manifest identity mismatch",
        )
        for c in data["captures"]:
            raw = storage_bytes(repo, c["storage"])
            require(
                len(raw) == c["bytes"]
                and digest(raw) == c["sha256"]
                and png(raw) == c["dimensions"],
                "stored object integrity mismatch",
            )
        count += 1
    for event_path in sorted((root / "events").glob("*.json")):
        raw = safe_path(root, str(event_path.relative_to(root))).read_bytes()
        require(event_path.stem == digest(raw), "event digest mismatch")
        validate_event(repo, json.loads(raw))
    return count


def validate_event(repo: Path, event: dict) -> None:
    require(
        set(event)
        == {
            "schemaVersion",
            "kind",
            "manifest",
            "manifestSha256",
            "captureHashes",
            "conclusion",
            "evidence",
            "notes",
        },
        "unexpected event fields",
    )
    require(
        event["schemaVersion"] == 1 and event["kind"] in {"technical-review", "native-validation"},
        "invalid event kind",
    )
    root = repo / "evidence/visual"
    require(
        re.fullmatch(r"runs/[0-9]+-[0-9]+-[0-9]+-[0-9]+\.json", event["manifest"]) is not None,
        "invalid event target",
    )
    raw = safe_path(root, event["manifest"]).read_bytes()
    require(digest(raw) == event["manifestSha256"], "event target mismatch")
    target = json.loads(raw)
    validate_manifest(target)
    hashes = event["captureHashes"]
    require(
        isinstance(hashes, list)
        and bool(hashes)
        and len(hashes) == len(set(hashes))
        and set(hashes) <= {c["sha256"] for c in target["captures"]},
        "invalid event captures",
    )
    require(
        isinstance(event["notes"], str)
        and 0 < len(event["notes"]) <= 2000
        and "://" not in event["notes"],
        "invalid review notes",
    )
    if event["kind"] == "technical-review":
        require(
            event["conclusion"] in {"intended-change", "defect-found", "inconclusive"},
            "invalid review conclusion",
        )
        require(
            event["evidence"] == "actual-expected-diff-pixels-inspected",
            "review must describe pixel inspection",
        )
    else:
        require(
            event["conclusion"] in {"passed", "failed", "timedOut", "interrupted"},
            "invalid validation conclusion",
        )
        require(
            re.fullmatch(r"runs/[0-9]+-[0-9]+-[0-9]+-[0-9]+\.json", event["evidence"]) is not None,
            "validation requires retained native manifest",
        )
        native = json.loads(safe_path(root, event["evidence"]).read_bytes())
        validate_manifest(native)
        require(native["originalOutcome"] == event["conclusion"], "validation outcome mismatch")
        require(native["runId"] != target["runId"], "validation must be a later native run")
        require(native["runId"] > target["runId"], "validation predates original run")
        wanted = {
            (c["test"], c["project"], tuple(c["viewport"]))
            for c in target["captures"]
            if c["sha256"] in hashes
        }
        observed = {
            (c["test"], c["project"], tuple(c["viewport"]))
            for c in native["captures"]
            if c["originalOutcome"] == event["conclusion"]
        }
        require(wanted <= observed, "validation does not cover selected tests")


def append_event(repo: Path, event: dict) -> Path:
    validate_archive(repo)
    validate_event(repo, event)
    raw = canonical(event)
    path = safe_path(repo / "evidence/visual", f"events/{digest(raw)}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists() or path.read_bytes() == raw, "event integrity conflict")
    if not path.exists():
        with path.open("xb") as stream:
            stream.write(raw)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--require-runs", action="store_true")
    parser.add_argument("--git-transfer", action="store_true")
    parser.add_argument("--event", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    require(
        not (args.event and (args.archive or args.manifest or args.git_transfer)),
        "event cannot be combined with import",
    )
    if args.event:
        print(append_event(args.repo, json.loads(args.event.read_text())))
    elif args.git_transfer:
        require(bool(args.manifest) and not args.archive, "Git transfer requires only manifest")
        print(import_git_transfer(args.repo, json.loads(args.manifest.read_text())))
    elif args.archive or args.manifest:
        require(bool(args.archive and args.manifest), "archive and manifest required together")
        print(import_archive(args.repo, args.archive, json.loads(args.manifest.read_text())))
    else:
        count = validate_archive(args.repo)
        require(not args.require_runs or count > 0, "required archive has no run manifests")
        print(json.dumps({"validatedRunManifests": count, "acceptanceGranted": False}))


if __name__ == "__main__":
    main()
