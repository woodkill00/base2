from __future__ import annotations

import json
import struct
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from digital_ocean.scripts.python.preview_control import (
    PreviewControlError,
    _parser,
    _receipt,
    execute,
    launch_from_config,
    mutation_lock,
    prove_exact_main,
    validate_launch_config,
)
from digital_ocean.scripts.python.preview_dns_convergence import (
    DnsConvergenceError,
    classify_dns_observation,
)
from digital_ocean.scripts.python.preview_expiry import (
    ExpiryPlanError,
    arm_expiry,
    build_expiry_plan,
    extend_lease,
    systemd_run_arguments,
)
from digital_ocean.scripts.python.preview_inventory import (
    InventoryError,
    admit_private_root,
    inventory,
)
from digital_ocean.scripts.python.preview_lease_v2 import FullPreviewLeaseStore
from digital_ocean.scripts.python.preview_provider_inventory import (
    ProviderInventoryError,
    reconcile_provider_inventory,
)
from digital_ocean.scripts.python.preview_retention import RetentionError, cleanup_visual_evidence
from digital_ocean.scripts.python.preview_runtime import RuntimeAdmissionError, inspect_runtime
from digital_ocean.scripts.python.preview_visual_evidence import (
    REQUIRED_FILES,
    VisualEvidenceError,
    _required_names,
    build_visual_bundle,
)
from scripts.python.visual_asset_policy import scan_assets

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
RUN = "base2-full-20260826-120000"


def lease_payload(**overrides):
    value = {
        "schemaVersion": 2,
        "runId": RUN,
        "state": "live-verified",
        "armedAt": NOW.isoformat().replace("+00:00", "Z"),
        "expiresAt": (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "sourceCommit": "a" * 40,
        "sourceArchiveSha256": "b" * 64,
        "profileId": "base2-obsidian",
        "profileDigest": "c" * 64,
        "droplet": {
            "id": "123",
            "name": "base2-full-preview",
            "tags": [RUN, "base2-full-preview"],
            "size": "s-2vcpu-2gb",
            "createdAt": NOW.isoformat().replace("+00:00", "Z"),
        },
        "dnsRecords": [
            {
                "id": "41",
                "domain": "woodkilldev.com",
                "type": "A",
                "name": "@",
                "value": "203.0.113.8",
                "state": "bound",
            },
        ],
        "ownerAdmissionDigest": "d" * 64,
        "certificateMode": "letsencrypt-staging-only",
        "budgetCeilingUsd": "0.25",
        "lastError": None,
        "mutationCounts": {"dropletsDeleted": 0, "dnsRecordsDeleted": 0},
    }
    value.update(overrides)
    return value


def state_with_lease(tmp_path: Path, **overrides) -> tuple[Path, Path]:
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    lease_root = state / RUN / "leases"
    FullPreviewLeaseStore(lease_root).create(lease_payload(**overrides))
    return state, lease_root


def dns_payload():
    hosts = ["woodkilldev.com", "admin.woodkilldev.com"]
    answers = [{"host": host, "type": "A", "address": "203.0.113.8", "ttl": 60} for host in hosts]
    return {
        "schemaVersion": 1,
        "domain": "woodkilldev.com",
        "expectedAddress": "203.0.113.8",
        "requiredHosts": hosts,
        "sources": [
            {
                "sourceClass": "provider-authoritative",
                "sourceName": "digitalocean",
                "observedAt": "2026-08-26T12:00:00Z",
                "answers": [dict(row) for row in answers],
            },
            {
                "sourceClass": "public-recursive",
                "sourceName": "google",
                "observedAt": "2026-08-26T12:00:01Z",
                "answers": [dict(row) for row in answers],
            },
            {
                "sourceClass": "system-recursive",
                "sourceName": "wsl",
                "observedAt": "2026-08-26T12:00:02Z",
                "answers": [dict(row) for row in answers],
            },
        ],
    }


def tiny_png() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 10, 12)


def visual_root(tmp_path: Path, *, complete: bool = True) -> Path:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    evidence = private / "browser"
    evidence.mkdir()
    names = sorted(_required_names()) if complete else sorted(REQUIRED_FILES)
    for name in names:
        (evidence / name).write_bytes(tiny_png())
    return evidence


def test_actual_runtime_is_native_wsl_and_credential_free():
    result = inspect_runtime(ROOT)
    assert result["ok"] and result["credentialReads"] == 0
    assert {row["binaryClass"] for row in result["tools"]} <= {"linux-elf", "linux-script"}
    assert all(
        "/mnt/" not in row["path"] and not row["path"].endswith(".exe") for row in result["tools"]
    )


def test_runtime_rejects_windows_tool_before_access():
    tools = {
        name: "/usr/bin/python3" for name in ("python3", "node", "npm", "git", "ssh", "docker")
    }
    tools["npm"] = "C:\\Program Files\\nodejs\\npm.cmd"
    with pytest.raises(RuntimeAdmissionError) as failure:
        inspect_runtime(ROOT, proc_version="Microsoft WSL2", machine="x86_64", tool_paths=tools)
    assert failure.value.code == "RUNTIME_WINDOWS_TOOL"


def test_runtime_rejects_non_wsl_and_mounted_repository(tmp_path):
    with pytest.raises(RuntimeAdmissionError) as failure:
        inspect_runtime(tmp_path)
    assert failure.value.code == "RUNTIME_NON_WSL_REPOSITORY"


def test_inventory_classifies_expiry_and_destroyed_leases(tmp_path):
    state, lease_root = state_with_lease(tmp_path)
    result = inventory(state, now=NOW + timedelta(hours=2))
    assert result["counts"] == {"expired": 1}
    assert result["leases"][0]["exactAddress"] == "203.0.113.8"
    store = FullPreviewLeaseStore(lease_root)
    value = store.load(RUN)
    value["state"] = "destroyed"
    value["mutationCounts"] = {"dropletsDeleted": 1, "dnsRecordsDeleted": 1}
    value["dnsRecords"][0]["state"] = "absent"
    store.replace(value)
    assert inventory(state, now=NOW + timedelta(hours=2))["counts"] == {"destroyed": 1}


def test_inventory_rejects_public_root_and_reports_tamper(tmp_path):
    tmp_path.chmod(0o755)
    with pytest.raises(InventoryError):
        inventory(tmp_path)
    tmp_path.chmod(0o700)
    state, lease_root = state_with_lease(tmp_path)
    path = lease_root / f"{RUN}.json"
    path.write_text(path.read_text().replace("live-verified", "destroyed"))
    result = inventory(state)
    assert result["code"] == "LEASE_INTEGRITY_INVALID" and result["invalid"]


def test_dns_converged_is_deterministic_and_ttl_can_be_unknown():
    payload = dns_payload()
    payload["sources"][2]["answers"][0].pop("ttl")
    first = classify_dns_observation(payload)
    second = classify_dns_observation(payload)
    assert first == second and first["code"] == "OK"
    system = next(row for row in first["sources"] if row["sourceClass"] == "system-recursive")
    assert any(answer["ttl"] is None for answer in system["answers"])


def test_dns_stale_system_is_distinct_from_public_split():
    stale = dns_payload()
    stale["sources"][2]["answers"][0]["address"] = "198.51.100.9"
    assert classify_dns_observation(stale)["code"] == "DNS_STALE_RECURSIVE"
    split = dns_payload()
    split["sources"][1]["answers"][0]["address"] = "198.51.100.9"
    assert classify_dns_observation(split)["code"] == "DNS_SPLIT_VIEW"


def test_dns_unexpected_ipv6_and_duplicate_answer_fail_closed():
    value = dns_payload()
    value["sources"][1]["answers"].append(
        {"host": "woodkilldev.com", "type": "AAAA", "address": "2001:db8::1", "ttl": 60}
    )
    assert classify_dns_observation(value)["code"] == "DNS_UNEXPECTED_IPV6"
    duplicate = dns_payload()
    duplicate["sources"][0]["answers"].append(dict(duplicate["sources"][0]["answers"][0]))
    with pytest.raises(DnsConvergenceError):
        classify_dns_observation(duplicate)


def test_expiry_plan_is_fixed_integrity_bound_and_persistent(tmp_path):
    _, lease_root = state_with_lease(
        tmp_path, expiresAt="2026-08-26T13:00:43.578547Z"
    )
    credential = tmp_path / "credential.json"
    credential.write_text("{}")
    credential.chmod(0o600)
    plan = build_expiry_plan(
        lease_root=lease_root,
        run_id=RUN,
        credential_file=credential,
        python_executable=sys.executable,
        repo_root=ROOT,
    )
    args = systemd_run_arguments(plan)
    assert "--timer-property=Persistent=true" in args
    assert "--on-calendar=2026-08-26 13:00:43 UTC" in args
    assert "digital_ocean.scripts.python.full_preview_expire" in args
    assert "--early-approved" not in args
    assert str(credential) in args and plan["secretValuesEmitted"] == 0


def test_expiry_plan_tamper_and_nonlive_lease_reject(tmp_path):
    _, lease_root = state_with_lease(tmp_path)
    credential = tmp_path / "credential.json"
    credential.write_text("{}")
    credential.chmod(0o600)
    plan = build_expiry_plan(
        lease_root=lease_root,
        run_id=RUN,
        credential_file=credential,
        python_executable=sys.executable,
        repo_root=ROOT,
    )
    plan["expiresAt"] = "2027-01-01T00:00:00Z"
    with pytest.raises(ExpiryPlanError):
        systemd_run_arguments(plan)


def test_arm_expiry_uses_argument_vector_and_reports_failure(tmp_path):
    _, lease_root = state_with_lease(tmp_path)
    credential = tmp_path / "credential.json"
    credential.write_text("{}")
    credential.chmod(0o600)
    plan = build_expiry_plan(
        lease_root=lease_root,
        run_id=RUN,
        credential_file=credential,
        python_executable=sys.executable,
        repo_root=ROOT,
    )
    calls = []

    class Result:
        returncode = 0
        stdout = "ActiveState=active\nLoadState=loaded\n"
        stderr = ""

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        return Result()

    assert arm_expiry(plan, runner=runner)["armed"] is True
    assert isinstance(calls[0][0], list) and calls[0][1]["timeout"] == 20
    Result.returncode = 1
    with pytest.raises(ExpiryPlanError) as failure:
        arm_expiry(plan, runner=runner)
    assert failure.value.code == "EXPIRY_NOT_ARMED"


def test_provider_inventory_is_read_only_exact_and_rate_limit_is_typed(tmp_path):
    state, _ = state_with_lease(
        tmp_path,
        state="destroyed",
        mutationCounts={"dropletsDeleted": 1, "dnsRecordsDeleted": 1},
        dnsRecords=[
            {
                "id": "41",
                "domain": "woodkilldev.com",
                "type": "A",
                "name": "@",
                "value": "203.0.113.8",
                "state": "absent",
            }
        ],
    )
    leases = inventory(state)

    class Droplets:
        def __init__(self, rows):
            self.rows, self.calls = rows, []

        def list(self, **kwargs):
            self.calls.append(kwargs)
            return {"droplets": self.rows}

    empty = Droplets([])
    result = reconcile_provider_inventory(empty, leases)
    assert result["ok"] and result["providerActions"] == 0
    assert empty.calls == [{"tag_name": "base2-full-preview"}]
    orphan = Droplets(
        [
            {
                "id": 999,
                "name": "base2-full-preview",
                "status": "active",
                "tags": ["base2-full-preview"],
            }
        ]
    )
    assert reconcile_provider_inventory(orphan, leases)["orphanedDropletIds"] == ["999"]

    class Limited:
        def list(self, **kwargs):
            error = RuntimeError("limited")
            error.status_code = 429
            error.retry_after = 30
            raise error

    with pytest.raises(ProviderInventoryError) as failure:
        reconcile_provider_inventory(Limited(), leases)
    assert failure.value.code == "PROVIDER_RATE_LIMITED" and failure.value.retry_after == 30

    class Recovers:
        calls = 0

        def list(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                error = RuntimeError("limited")
                error.status_code = 429
                error.retry_after = 1
                raise error
            return {"droplets": []}

    waits = []
    recovered = reconcile_provider_inventory(Recovers(), leases, sleeper=waits.append)
    assert recovered["ok"] and recovered["attempts"] == 2 and waits == [1.0]


def test_extension_is_bounded_and_rejects_expired(tmp_path):
    _, lease_root = state_with_lease(tmp_path)
    result = extend_lease(lease_root=lease_root, run_id=RUN, minutes=30, now=NOW)
    assert result["expiresAt"] == "2026-08-26T13:30:00Z"
    with pytest.raises(ExpiryPlanError):
        extend_lease(lease_root=lease_root, run_id=RUN, minutes=60, now=NOW)


def test_complete_visual_bundle_is_hashed_private_and_deterministic(tmp_path):
    root = visual_root(tmp_path)
    first = build_visual_bundle(
        evidence_root=root, commit="a" * 40, profile_digest="b" * 64, run_id=RUN
    )
    second = build_visual_bundle(
        evidence_root=root, commit="a" * 40, profile_digest="b" * 64, run_id=RUN
    )
    assert first == second and first["ok"]
    assert first["artifactCount"] == len(_required_names())
    assert {"browser", "viewport", "route", "state"} <= set(first["artifacts"][0])
    assert (root / "visual-evidence.json").stat().st_mode & 0o777 == 0o600
    assert (root / "visual-evidence.html").stat().st_mode & 0o777 == 0o600


def test_visual_bundle_reports_missing_and_rejects_symlink(tmp_path):
    root = visual_root(tmp_path, complete=False)
    assert (
        build_visual_bundle(
            evidence_root=root, commit="a" * 40, profile_digest="b" * 64, run_id=RUN
        )["code"]
        == "EVIDENCE_INCOMPLETE"
    )
    target = root / "admin.png"
    target.unlink()
    target.symlink_to(root / "swagger.png")
    with pytest.raises((OSError, VisualEvidenceError)):
        build_visual_bundle(
            evidence_root=root, commit="a" * 40, profile_digest="b" * 64, run_id=RUN
        )


def test_visual_review_is_escaped_and_never_changes_baselines(tmp_path):
    root = visual_root(tmp_path)
    review = root / "visual-review.json"
    review.write_text(
        json.dumps(
            {"state": "rejected", "feedback": "<script>alert(1)</script>", "reviewer": "owner"}
        )
    )
    result = build_visual_bundle(
        evidence_root=root, commit="a" * 40, profile_digest="b" * 64, run_id=RUN
    )
    page = (root / "visual-evidence.html").read_text()
    assert result["review"]["state"] == "rejected"
    assert "<script>alert(1)</script>" not in page


def test_current_svg_assets_pass_and_active_svg_or_raster_fail(tmp_path):
    assert scan_assets(ROOT / "react-app/src/assets")["ok"]
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "unsafe.svg").write_text('<svg viewBox="0 0 1 1"><script>alert(1)</script></svg>')
    (bad / "unnamed.svg").write_text('<svg viewBox="0 0 1 1" role="img"/>')
    (bad / "button.png").write_bytes(b"raster")
    codes = {row["code"] for row in scan_assets(bad)["findings"]}
    assert {"SVG_ACTIVE_CONTENT", "SVG_ACCESSIBLE_NAME_REQUIRED", "UNCLASSIFIED_RASTER"} <= codes
    content = bad / "content"
    content.mkdir()
    (content / "photo.jpg").write_bytes(b"photo")
    assert not any(row["path"] == "content/photo.jpg" for row in scan_assets(bad)["findings"])


def test_launch_config_rejects_unknown_fields_and_invalid_ttl():
    value = {
        field: "x"
        for field in __import__(
            "digital_ocean.scripts.python.preview_control", fromlist=["LAUNCH_FIELDS"]
        ).LAUNCH_FIELDS
    }
    value.update({"schemaVersion": 1, "runId": RUN, "sshKeyId": 1, "ttlMinutes": 60})
    assert validate_launch_config(value)["runId"] == RUN
    with pytest.raises(PreviewControlError):
        validate_launch_config({**value, "command": "rm -rf /"})
    with pytest.raises(PreviewControlError):
        validate_launch_config({**value, "ttlMinutes": 600})


def test_launch_orchestration_arms_expiry_and_cleans_up_if_arming_fails(tmp_path, monkeypatch):
    import digital_ocean.scripts.python.preview_control as control

    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    files = {}
    for name in (
        "credentialFile",
        "sshPrivateKey",
        "operatorAuthFile",
        "flowerAuthFile",
        "probeUsernameFile",
        "probePasswordFile",
        "djangoUsernameFile",
        "djangoEmailFile",
        "djangoPasswordFile",
        "pgadminEmailFile",
        "pgadminPasswordFile",
    ):
        path = private / name
        path.write_text(
            json.dumps({"secrets": {"DO_API_TOKEN": "unit-test-token"}})
            if name == "credentialFile"
            else "value"
        )
        path.chmod(0o600)
        files[name] = str(path)
    config = {
        "schemaVersion": 1,
        "repoRoot": str(ROOT),
        "stateRoot": str(state),
        "runId": RUN,
        "domain": "woodkilldev.com",
        "ownerCidr": "203.0.113.7/32",
        "ttlMinutes": 60,
        "profilePath": str(ROOT / "site_profiles/base2-obsidian.json"),
        "sourceArchiveDir": str(source),
        "sshKeyId": 1,
        "pythonExecutable": sys.executable,
        **files,
    }
    monkeypatch.setattr(control, "inspect_runtime", lambda repo: {"ok": True})
    monkeypatch.setattr(control, "prove_exact_main", lambda repo, runner: "a" * 40)

    class Droplets:
        def list(self, **kwargs):
            return {"droplets": []}

    class Client:
        droplets = Droplets()

    class Result:
        def __init__(self, code=0, output=""):
            self.returncode, self.stdout, self.stderr = code, output, ""

    def lifecycle_runner(args, **kwargs):
        if args[:2] == ["git", "archive"]:
            output = next(item.split("=", 1)[1] for item in args if item.startswith("--output="))
            Path(output).write_bytes(b"archive")
            return Result()
        if "digital_ocean.scripts.python.full_preview_live" in args:
            lease_root = state / RUN / "leases"
            FullPreviewLeaseStore(lease_root).create(lease_payload(sourceCommit="a" * 40))
            return Result(
                output=json.dumps({"ok": True, "status": "live-verified", "secretValuesEmitted": 0})
            )
        if "digital_ocean.scripts.python.full_preview_expire" in args:
            return Result(
                output=json.dumps({"ok": True, "state": "destroyed", "secretValuesEmitted": 0})
            )
        raise AssertionError(args)

    class TimerResult:
        returncode = 0
        stdout = "ActiveState=active\nLoadState=loaded\n"
        stderr = ""

    result = launch_from_config(
        config,
        runner=lifecycle_runner,
        timer_runner=lambda *args, **kwargs: TimerResult(),
        provider_factory=lambda token: Client(),
    )
    assert result["expiry"]["armed"] and result["budgetCeilingUsd"] == "0.25"
    intent = json.loads((state / "intents" / f"{RUN}.json").read_text())
    assert intent["state"] == "live-bounded" and "expiryPlanDigest" in intent

    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    config["stateRoot"] = str(other)

    class FailedTimer:
        returncode = 1
        stdout = ""
        stderr = "failed"

    with pytest.raises(PreviewControlError) as failure:
        launch_from_config(
            config,
            runner=lifecycle_runner,
            timer_runner=lambda *args, **kwargs: FailedTimer(),
            provider_factory=lambda token: Client(),
        )
    assert failure.value.code == "EXPIRY_NOT_ARMED"
    assert failure.value.cleanup_state == "destroyed"


def test_exact_main_admission_rejects_dirty_or_divergent_source(tmp_path):
    class Result:
        def __init__(self, output="", code=0):
            self.stdout, self.stderr, self.returncode = output, "", code

    outputs = iter([Result(""), Result("a" * 40), Result("a" * 40), Result("a" * 40)])
    assert prove_exact_main(tmp_path, runner=lambda *args, **kwargs: next(outputs)) == "a" * 40
    dirty = iter([Result(" M unsafe")])
    with pytest.raises(PreviewControlError) as failure:
        prove_exact_main(tmp_path, runner=lambda *args, **kwargs: next(dirty))
    assert failure.value.code == "SOURCE_NOT_EXACT_MAIN"


def test_mutation_lock_fails_closed_and_receipt_redacts_control_values(tmp_path):
    tmp_path.chmod(0o700)
    with (
        mutation_lock(tmp_path),
        pytest.raises(PreviewControlError) as failure,
        mutation_lock(tmp_path),
    ):
        pass
    assert failure.value.code == "LEASE_CONFLICT"
    receipt = _receipt(
        "test",
        ok=False,
        code="LIFECYCLE_EXTERNAL_FAILURE",
        details={},
        summary="bad\nBearer " + ("a" * 26),
    )
    assert "\n" not in receipt["summary"] and "[REDACTED]" in receipt["summary"]


def test_bash_entrypoint_is_wsl_only_and_uses_argument_vector():
    script = (ROOT / "digital_ocean/scripts/bash/base2-preview.sh").read_text()
    assert "WSL_DISTRO_NAME" in script and "/home/*" in script
    assert "RUNTIME_WINDOWS_TOOL" in script
    assert 'exec "$python_bin" -m digital_ocean.scripts.python.preview_control "$@"' in script
    assert "eval " not in script and "bash -c" not in script


def test_cli_emits_one_json_object_stable_exit_codes_and_failure_outbox(tmp_path):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    command = [
        sys.executable,
        "-m",
        "digital_ocean.scripts.python.preview_control",
    ]
    success = subprocess.run(
        [*command, "status", "--state-root", str(state)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert success.returncode == 0 and len(success.stdout.splitlines()) == 1
    assert json.loads(success.stdout)["secretValuesEmitted"] == 0

    config = tmp_path / "launch.json"
    config.write_text(json.dumps({"schemaVersion": 1, "stateRoot": str(state)}))
    config.chmod(0o600)
    failure = subprocess.run(
        [*command, "launch", "--config", str(config)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(failure.stdout)
    assert failure.returncode == 5 and receipt["code"] == "LAUNCH_CONFIG_INVALID"
    assert len(failure.stdout.splitlines()) == 1 and failure.stderr == ""
    outbox = list((state / "outbox").glob("failure-*.json"))
    assert len(outbox) == 1 and json.loads(outbox[0].read_text())["secretValuesEmitted"] == 0


def test_execute_routes_read_only_and_bounded_mutation_commands(tmp_path, monkeypatch):
    import digital_ocean.scripts.python.preview_control as control

    state, lease_root = state_with_lease(tmp_path)
    credential = tmp_path / "credential.json"
    credential.write_text(json.dumps({"secrets": {"DO_API_TOKEN": "test"}}))
    credential.chmod(0o600)
    observation = tmp_path / "dns.json"
    observation.write_text(json.dumps(dns_payload()))
    observation.chmod(0o600)
    evidence = visual_root(tmp_path)

    class Droplets:
        def list(self, **kwargs):
            return {"droplets": []}

    class Client:
        droplets = Droplets()

    monkeypatch.setattr(control, "_token", lambda path: "test")
    monkeypatch.setattr(control, "DigitalOceanHttpClient", lambda token: Client())

    commands = [
        ["preflight", "--repo", str(ROOT)],
        ["status", "--state-root", str(state)],
        [
            "provider-status",
            "--state-root",
            str(state),
            "--credential-file",
            str(credential),
        ],
        ["dns", "--observation", str(observation)],
        [
            "evidence",
            "--evidence-root",
            str(evidence),
            "--commit",
            "a" * 40,
            "--profile-digest",
            "b" * 64,
            "--run-id",
            RUN,
        ],
        [
            "arm-expiry",
            "--lease-root",
            str(lease_root),
            "--run-id",
            RUN,
            "--credential-file",
            str(credential),
            "--python-executable",
            sys.executable,
            "--repo-root",
            str(ROOT),
        ],
        ["verify", "--state-root", str(state), "--run-id", RUN],
        ["retention", "--state-root", str(state)],
    ]
    results = [execute(_parser().parse_args(command)) for command in commands]
    assert results[2][1] == 3 and results[2][0]["code"] == "LEASE_CONFLICT"
    assert all(
        code == 0 and receipt["secretValuesEmitted"] == 0
        for index, (receipt, code) in enumerate(results)
        if index != 2
    )
    verify = results[-2][0]["details"]
    assert verify["exactAddressBrowserTarget"] == "203.0.113.8"

    monkeypatch.setattr(control, "extend_lease", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(control, "build_expiry_plan", lambda **kwargs: {"unit": "fixed"})
    monkeypatch.setattr(control, "arm_expiry", lambda plan: {"armed": True})
    monkeypatch.setattr(
        control.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )
    extended, code = execute(
        _parser().parse_args(
            [
                "extend",
                "--lease-root",
                str(lease_root),
                "--run-id",
                RUN,
                "--minutes",
                "10",
                "--credential-file",
                str(credential),
                "--python-executable",
                sys.executable,
                "--repo-root",
                str(ROOT),
            ]
        )
    )
    assert code == 0 and extended["details"]["expiry"]["armed"]

    launch_config = tmp_path / "valid-shape.json"
    launch_value = {field: "x" for field in control.LAUNCH_FIELDS}
    launch_value["stateRoot"] = str(state)
    launch_config.write_text(json.dumps(launch_value))
    launch_config.chmod(0o600)
    monkeypatch.setattr(control, "launch_from_config", lambda config: {"ok": True})
    launched, code = execute(_parser().parse_args(["launch", "--config", str(launch_config)]))
    assert code == 0 and launched["ok"]


def test_retention_is_bounded_to_old_unapproved_visual_evidence(tmp_path):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    run_ids = [
        "base2-full-20260701-120000",
        "base2-full-20260702-120000",
        "base2-full-20260703-120000",
    ]
    for run_id in run_ids:
        lease_root = state / run_id / "leases"
        payload = lease_payload(
            runId=run_id,
            state="destroyed",
            droplet={
                "id": "123",
                "name": "base2-full-preview",
                "tags": [run_id, "base2-full-preview"],
                "size": "s-2vcpu-2gb",
                "createdAt": NOW.isoformat().replace("+00:00", "Z"),
            },
            mutationCounts={"dropletsDeleted": 1, "dnsRecordsDeleted": 1},
            dnsRecords=[
                {
                    "id": "41",
                    "domain": "woodkilldev.com",
                    "type": "A",
                    "name": "@",
                    "value": "203.0.113.8",
                    "state": "absent",
                }
            ],
        )
        FullPreviewLeaseStore(lease_root).create(payload)
        evidence = state / run_id / "browser-exact"
        evidence.mkdir(mode=0o700)
        (evidence / "capture.png").write_bytes(tiny_png())
    approved = state / run_ids[0] / "browser-exact" / "visual-review.json"
    approved.write_text(json.dumps({"state": "approved", "feedback": "", "reviewer": "owner"}))
    plan = cleanup_visual_evidence(state, now=NOW, keep_runs=1)
    assert plan["candidateCount"] == 1
    assert plan["approvedEvidenceSkipped"] == [f"{run_ids[0]}/browser-exact"]
    applied = cleanup_visual_evidence(state, now=NOW, keep_runs=1, apply=True)
    assert len(applied["deleted"]) == 1
    assert (state / run_ids[1] / "leases" / f"{run_ids[1]}.json").exists()
    assert (state / run_ids[0] / "browser-exact" / "capture.png").exists()


def test_dns_hostile_shapes_fail_closed():
    variants = []
    missing_field = dns_payload()
    missing_field.pop("domain")
    variants.append(missing_field)
    bad_domain = dns_payload()
    bad_domain["domain"] = "not a domain"
    variants.append(bad_domain)
    duplicate_hosts = dns_payload()
    duplicate_hosts["requiredHosts"].append("woodkilldev.com")
    variants.append(duplicate_hosts)
    bad_source_shape = dns_payload()
    bad_source_shape["sources"][0]["extra"] = True
    variants.append(bad_source_shape)
    bad_source_identity = dns_payload()
    bad_source_identity["sources"][0]["sourceClass"] = "unknown"
    variants.append(bad_source_identity)
    bad_time = dns_payload()
    bad_time["sources"][0]["observedAt"] = "yesterday"
    variants.append(bad_time)
    bad_answer_shape = dns_payload()
    bad_answer_shape["sources"][0]["answers"][0]["extra"] = True
    variants.append(bad_answer_shape)
    outside_host = dns_payload()
    outside_host["sources"][0]["answers"][0]["host"] = "example.net"
    variants.append(outside_host)
    bad_address = dns_payload()
    bad_address["sources"][0]["answers"][0]["address"] = "999.1.1.1"
    variants.append(bad_address)
    type_mismatch = dns_payload()
    type_mismatch["sources"][0]["answers"][0].update({"type": "AAAA", "address": "203.0.113.8"})
    variants.append(type_mismatch)
    bad_ttl = dns_payload()
    bad_ttl["sources"][0]["answers"][0]["ttl"] = 999999
    variants.append(bad_ttl)
    missing_public = dns_payload()
    missing_public["sources"] = missing_public["sources"][:1]
    variants.append(missing_public)
    for payload in variants:
        with pytest.raises(DnsConvergenceError):
            classify_dns_observation(payload)


def test_runtime_hostile_tools_architecture_and_environment_fail_closed(tmp_path, monkeypatch):
    tools = {
        name: "/usr/bin/python3" for name in ("python3", "node", "npm", "git", "ssh", "docker")
    }
    invalid = tmp_path / "invalid-tool"
    invalid.write_text("not executable content")
    tools["node"] = str(invalid)
    with pytest.raises(RuntimeAdmissionError) as failure:
        inspect_runtime(ROOT, proc_version="Microsoft WSL2", machine="x86_64", tool_paths=tools)
    assert failure.value.code == "RUNTIME_TOOL_INVALID"
    with pytest.raises(RuntimeAdmissionError) as failure:
        inspect_runtime(ROOT, proc_version="Microsoft WSL2", machine="sparc", tool_paths=tools)
    assert failure.value.code == "RUNTIME_ARCH_INVALID"
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    with pytest.raises(RuntimeAdmissionError) as failure:
        inspect_runtime(ROOT, proc_version="Linux", machine="x86_64", tool_paths=tools)
    assert failure.value.code == "RUNTIME_NOT_WSL"
    with pytest.raises(RuntimeAdmissionError) as failure:
        inspect_runtime(ROOT, proc_version="Microsoft WSL2", machine="x86_64", tool_paths={})
    assert failure.value.code == "RUNTIME_TOOL_MISSING"


def test_visual_hostile_metadata_corruption_and_size_fail_closed(tmp_path):
    root = visual_root(tmp_path)
    review = root / "visual-review.json"
    review.write_text("not-json")
    with pytest.raises(VisualEvidenceError):
        build_visual_bundle(
            evidence_root=root, commit="a" * 40, profile_digest="b" * 64, run_id=RUN
        )
    review.unlink()
    corrupt = root / "admin.png"
    corrupt.write_bytes(b"not-png")
    with pytest.raises(VisualEvidenceError):
        build_visual_bundle(
            evidence_root=root, commit="a" * 40, profile_digest="b" * 64, run_id=RUN
        )
    corrupt.write_bytes(tiny_png())
    with pytest.raises(VisualEvidenceError):
        build_visual_bundle(evidence_root=root, commit="bad", profile_digest="b" * 64, run_id=RUN)


def test_control_input_and_lifecycle_receipt_validation_fail_closed(tmp_path):
    import digital_ocean.scripts.python.preview_control as control

    private = tmp_path / "input.json"
    private.write_text("not-json")
    private.chmod(0o600)
    with pytest.raises(PreviewControlError):
        control._private_json(private, code="LAUNCH_CONFIG_INVALID")
    private.write_text("[]")
    with pytest.raises(PreviewControlError):
        control._private_json(private, code="LAUNCH_CONFIG_INVALID")
    private.chmod(0o644)
    with pytest.raises(PreviewControlError):
        control._private_json(private, code="LAUNCH_CONFIG_INVALID")

    class Result:
        def __init__(self, code, output):
            self.returncode, self.stdout, self.stderr = code, output, ""

    for result in (Result(1, ""), Result(0, "not-json"), Result(0, "{}")):
        with pytest.raises(PreviewControlError):
            control._run_json(
                ["fixed"], cwd=ROOT, runner=lambda *args, result=result, **kwargs: result
            )


def test_retention_invalid_policy_and_review_fail_closed(tmp_path):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    with pytest.raises(RetentionError):
        cleanup_visual_evidence(state, minimum_age_days=1)


def test_control_error_catalog_destroy_route_and_direct_main(tmp_path, monkeypatch, capsys):
    import digital_ocean.scripts.python.preview_control as control

    fields = {field: "x" for field in control.LAUNCH_FIELDS}
    fields.update({"schemaVersion": 1, "runId": RUN, "sshKeyId": 1, "ttlMinutes": 60})
    for change in (
        {"runId": "bad"},
        {"sshKeyId": 0},
        {"repoRoot": ""},
    ):
        with pytest.raises(PreviewControlError):
            validate_launch_config({**fields, **change})

    class Result:
        def __init__(self, output="", code=0):
            self.stdout, self.stderr, self.returncode = output, "", code

    for results in (
        [Result(""), Result(code=1)],
        [Result(""), Result("a" * 40), Result("b" * 40), Result("a" * 40)],
        [Result(""), Result("not-a-commit"), Result("not-a-commit"), Result("not-a-commit")],
    ):
        values = iter(results)
        with pytest.raises(PreviewControlError):
            prove_exact_main(tmp_path, runner=lambda *args, values=values, **kwargs: next(values))

    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    credential = tmp_path / "credential.json"
    credential.write_text("{}")
    credential.chmod(0o600)
    destroyed_inventory = {
        "leases": [],
        "unresolvedRunIds": [],
        "secretValuesEmitted": 0,
    }

    class Droplets:
        def list(self, **kwargs):
            return {"droplets": []}

    class Client:
        droplets = Droplets()

    monkeypatch.setattr(
        control,
        "_run_json",
        lambda *args, **kwargs: {"state": "destroyed", "secretValuesEmitted": 0},
    )
    monkeypatch.setattr(control, "inventory", lambda root: destroyed_inventory)
    monkeypatch.setattr(control, "_token", lambda path: "test")
    monkeypatch.setattr(control, "DigitalOceanHttpClient", lambda token: Client())
    destroyed, code = execute(
        _parser().parse_args(
            [
                "destroy",
                "--state-root",
                str(state),
                "--run-id",
                RUN,
                "--credential-file",
                str(credential),
                "--early-approved",
            ]
        )
    )
    assert code == 0 and destroyed["details"]["teardown"]["state"] == "destroyed"

    monkeypatch.setattr(control, "inventory", lambda root: (_ for _ in ()).throw(RuntimeError()))
    unexpected, code = execute(_parser().parse_args(["status", "--state-root", str(state)]))
    assert code == 5 and unexpected["cleanupState"] == "unknown"

    monkeypatch.setattr(control, "inventory", lambda root: destroyed_inventory)
    assert control.main(["status", "--state-root", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]


def test_expiry_and_inventory_hostile_boundaries(tmp_path):
    state, lease_root = state_with_lease(tmp_path)
    credential = tmp_path / "credential.json"
    credential.write_text("{}")
    credential.chmod(0o600)
    with pytest.raises(ExpiryPlanError):
        build_expiry_plan(
            lease_root=lease_root,
            run_id="bad",
            credential_file=credential,
            python_executable=sys.executable,
            repo_root=ROOT,
        )
    credential.chmod(0o644)
    with pytest.raises(ExpiryPlanError):
        build_expiry_plan(
            lease_root=lease_root,
            run_id=RUN,
            credential_file=credential,
            python_executable=sys.executable,
            repo_root=ROOT,
        )
    with pytest.raises(ExpiryPlanError):
        extend_lease(lease_root=lease_root, run_id=RUN, minutes=0, now=NOW)
    extend_lease(lease_root=lease_root, run_id=RUN, minutes=60, now=NOW)
    with pytest.raises(ExpiryPlanError):
        extend_lease(lease_root=lease_root, run_id=RUN, minutes=1, now=NOW)
    with pytest.raises(InventoryError):
        inventory(tmp_path / "missing")
    created = tmp_path / "created"
    control_inventory_root = admit_private_root(created, create=True)
    assert control_inventory_root.stat().st_mode & 0o077 == 0
