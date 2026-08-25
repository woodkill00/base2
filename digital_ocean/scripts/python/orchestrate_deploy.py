#!/usr/bin/env python3
"""
Orchestrate Digital Ocean Droplet deployment, DNS update, .env generation, and service startup.
- Requires: pydo, paramiko (for SSH/SCP), python-dotenv
- Usage: python orchestrate_deploy.py
"""

import argparse
import atexit
import concurrent.futures
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

import paramiko
from pydo import Client

try:
    from digital_ocean.scripts.python.deploy_config import load_deploy_config
except ModuleNotFoundError:
    from deploy_config import load_deploy_config

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _expand_env_templates(value: str, env: dict | None = None) -> str:
    """Expand simple ${VAR} templates using environment variables.

    This intentionally keeps behavior minimal:
    - Only supports ${NAME} (no default expressions like ${NAME:-x})
    - Unknown vars are left unchanged
    - Expansion is applied repeatedly a few times to allow chaining
    """
    if value is None:
        return value

    env_map = env or os.environ
    current = str(value)
    for _ in range(5):
        next_value = _ENV_VAR_PATTERN.sub(lambda m: env_map.get(m.group(1), m.group(0)), current)
        if next_value == current:
            break
        current = next_value
    return current


def _find_env_path() -> str:
    """Locate repo-root .env file.

    After script relocation to digital_ocean/scripts/python, we can't assume
    ../.env exists. Prefer APP_ENV_PATH/ENV_PATH if provided, else walk up
    parent directories looking for '.env'.
    """
    for key in ("APP_ENV_PATH", "ENV_PATH"):
        p = os.environ.get(key)
        if p and os.path.isfile(p):
            return os.path.abspath(p)

    # Prefer current working directory (deploy.ps1 Push-Location's to repo root)
    cwd_candidate = os.path.abspath(os.path.join(os.getcwd(), ".env"))
    if os.path.isfile(cwd_candidate):
        return cwd_candidate

    # Fall back: walk upwards from this file location
    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        candidate = parent / ".env"
        if candidate.is_file():
            return str(candidate)
    return cwd_candidate


def log(msg):
    print(f"\033[1;32m[INFO]\033[0m {msg}")


def err(msg):
    print(f"\033[1;31m[ERROR]\033[0m {msg}", flush=True)


def stage(msg):
    log(f"[STAGE] {msg}")


def log_json(label, data):
    print(f"\033[1;36m[DEBUG]\033[0m {label}: {json.dumps(data, indent=2)}")


def _safe_write(text: str, *, is_err: bool = False) -> None:
    stream = sys.stderr if is_err else sys.stdout
    try:
        stream.write(text)
    except UnicodeEncodeError:
        stream.buffer.write(text.encode("utf-8", errors="replace"))
    stream.flush()


def _do_api_call(label, func, *args, **kwargs):
    timeout_sec = int(os.getenv("DO_API_TIMEOUT_SECONDS", "30"))
    retries = int(os.getenv("DO_API_RETRY_COUNT", "3"))
    delay_sec = float(os.getenv("DO_API_RETRY_DELAY_SECONDS", "2"))
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError as exc:
            last_exc = exc
            err(f"{label} timed out after {timeout_sec}s (attempt {attempt}/{retries})")
        except Exception as exc:
            last_exc = exc
            err(f"{label} failed (attempt {attempt}/{retries}): {exc}")
        if attempt < retries:
            time.sleep(delay_sec)
    raise RuntimeError(f"{label} failed after {retries} attempts: {last_exc}")


# Parse configuration once, before provider identity or clients are created.
# Values already supplied by the process retain precedence, matching the prior
# dotenv behavior while eliminating multiple parsing implementations.
env_path = _find_env_path()
_DEPLOY_CONFIG = load_deploy_config(env_path)
for _key, _value in _DEPLOY_CONFIG.items():
    os.environ.setdefault(_key, _value)


# --- SSH Key Generation and .env Update ---
# --- Configurable timeouts and intervals ---
SSH_INITIAL_WAIT = 60  # seconds
SSH_ATTEMPTS = 3
SSH_INTERVAL = 20  # seconds
SSH_TIMEOUT = 15  # seconds
LOG_POLL_ATTEMPTS = 60
LOG_POLL_TIMEOUT = 30  # seconds
LOG_POLL_INTERVAL = 15  # seconds
IP_POLL_TIMEOUT = int(os.getenv("DO_IP_POLL_TIMEOUT_SECONDS", "120"))
IP_POLL_INTERVAL = int(os.getenv("DO_IP_POLL_INTERVAL_SECONDS", "5"))
REBOOT_MARKERS = ["Cloud-init v. 25.2-0ubuntu1~22.04.1 finished at"]
COMPLETION_MARKER = "User data script completed at"
SUMMARY = []
PROJECT_NAME = os.getenv("PROJECT_NAME", "app")
_EXPANSION_ENV = {**os.environ, "PROJECT_NAME": PROJECT_NAME}
ssh_dir = os.path.expanduser("~/.ssh")
ssh_key_path = os.path.join(ssh_dir, PROJECT_NAME)
pub_key_path = ssh_key_path + ".pub"

artifact_dir = os.getenv("DEPLOY_ARTIFACT_DIR", "").strip()
artifact_dir_path: Path | None = None
deploy_console_path: str | None = None
do_userdata_json_path = str(Path(__file__).resolve().parent / "DO_userdata.json")
_pending_artifact_rename: Path | None = None
_tee_stream = None


class _TeeStream:
    def __init__(self, primary, secondary):
        self._primary = primary
        self._secondary = secondary

    def write(self, data):
        self._primary.write(data)
        with suppress(Exception):
            self._secondary.write(data)

    def flush(self):
        self._primary.flush()
        with suppress(Exception):
            self._secondary.flush()

    def isatty(self):
        return self._primary.isatty()

    def close(self):
        with suppress(Exception):
            self._secondary.close()


def _init_artifacts() -> None:
    global artifact_dir_path, deploy_console_path, _tee_stream, do_userdata_json_path
    if not artifact_dir:
        return
    try:
        artifact_dir_path = Path(artifact_dir)
        artifact_dir_path.mkdir(parents=True, exist_ok=True)
        do_userdata_json_path = str(artifact_dir_path / "DO_userdata.json")
        deploy_console_path = str(artifact_dir_path / "deploy-console.log")
        try:
            log_file = open(deploy_console_path, "a", encoding="utf-8", errors="replace")  # noqa: SIM115
            _tee_stream = _TeeStream(sys.stdout, log_file)
            sys.stdout = _tee_stream
            sys.stderr = _TeeStream(sys.stderr, log_file)
        except Exception:
            _tee_stream = None
    except Exception as e:
        err(f"Failed to initialize DEPLOY_ARTIFACT_DIR '{artifact_dir}': {e}")
        artifact_dir_path = None
        deploy_console_path = None


def _plan_artifact_rename(ip_address: str) -> None:
    global _pending_artifact_rename
    if not artifact_dir_path or not ip_address:
        return
    name = artifact_dir_path.name
    if ip_address in name:
        return
    unknown_match = re.match(r"^unknown[-_](\d{8}_\d{6})$", name)
    stamp_match = re.match(r"^(\d{8}_\d{6})$", name)
    if unknown_match:
        stamp = unknown_match.group(1)
    elif stamp_match:
        stamp = stamp_match.group(1)
    else:
        return
    target = artifact_dir_path.parent / f"{ip_address}-{stamp}"
    if target == artifact_dir_path:
        return
    _pending_artifact_rename = target


def _reset_tee_stream(new_log_path: str) -> None:
    global _tee_stream
    try:
        primary_out = _tee_stream._primary if isinstance(_tee_stream, _TeeStream) else sys.stdout
        primary_err = sys.stderr
        if isinstance(primary_err, _TeeStream):
            primary_err = primary_err._primary
        if _tee_stream:
            _tee_stream.close()
        log_file = open(new_log_path, "a", encoding="utf-8", errors="replace")  # noqa: SIM115
        _tee_stream = _TeeStream(primary_out, log_file)
        sys.stdout = _tee_stream
        sys.stderr = _TeeStream(primary_err, log_file)
    except Exception:
        pass


def _apply_artifact_rename() -> None:
    global artifact_dir_path, deploy_console_path, do_userdata_json_path, _pending_artifact_rename
    if not artifact_dir_path or not _pending_artifact_rename:
        return
    original_path = artifact_dir_path
    target_path = _pending_artifact_rename
    try:
        if not target_path.exists():
            original_path.rename(target_path)
        artifact_dir_path = target_path
        deploy_console_path = str(artifact_dir_path / "deploy-console.log")
        do_userdata_json_path = str(artifact_dir_path / "DO_userdata.json")
        os.environ["DEPLOY_ARTIFACT_DIR"] = str(artifact_dir_path)
        _pending_artifact_rename = None
        _reset_tee_stream(deploy_console_path)
        return
    except Exception:
        pass

    try:
        target_path.mkdir(parents=True, exist_ok=True)
        for entry in original_path.iterdir():
            dest = target_path / entry.name
            if entry.is_dir():
                with suppress(Exception):
                    shutil.copytree(entry, dest, dirs_exist_ok=True)
            elif entry.is_file():
                with suppress(Exception):
                    shutil.copy2(entry, dest)
        with open(target_path / "artifact-alias.txt", "w", encoding="utf-8") as f:
            f.write(f"Original artifact path: {original_path}\n")
        with suppress(Exception):
            shutil.rmtree(original_path)
        artifact_dir_path = target_path
        deploy_console_path = str(artifact_dir_path / "deploy-console.log")
        do_userdata_json_path = str(artifact_dir_path / "DO_userdata.json")
        os.environ["DEPLOY_ARTIFACT_DIR"] = str(artifact_dir_path)
        _pending_artifact_rename = None
        _reset_tee_stream(deploy_console_path)
    except Exception:
        return


def _finalize_artifacts() -> None:
    global _tee_stream
    try:
        if _tee_stream:
            _tee_stream.close()
            _tee_stream = None
    except Exception:
        pass
    _apply_artifact_rename()


def _write_artifact_text(name: str, content: str) -> None:
    if not artifact_dir_path:
        return
    try:
        path = artifact_dir_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
    except Exception:
        pass


def _write_deploy_metadata(
    *, droplet_id: int | None, ip_address: str | None, update_only: bool
) -> None:
    if not artifact_dir_path:
        return
    payload = {
        "droplet_id": droplet_id,
        "ip_address": ip_address,
        "update_only": update_only,
        "create_if_missing": CREATE_IF_MISSING,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifact_dir": str(artifact_dir_path),
    }
    try:
        with open(artifact_dir_path / "deploy-meta.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def _record_ip_early(*, droplet_id: int | None, ip_address: str | None, update_only: bool) -> None:
    if not droplet_id or not ip_address:
        return
    log(f"[EARLY IP] Droplet {droplet_id} public IPv4: {ip_address}")
    _plan_artifact_rename(ip_address)
    _apply_artifact_rename()
    _write_deploy_metadata(droplet_id=droplet_id, ip_address=ip_address, update_only=update_only)


def _find_powershell_exe() -> str | None:
    for candidate in ("pwsh", "powershell"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def _run_bash_tests_suite() -> None:
    if not artifact_dir_path:
        err("Local tests requested but DEPLOY_ARTIFACT_DIR is not set.")
        raise RuntimeError("DEPLOY_ARTIFACT_DIR is required for local tests")

    bash_exe = shutil.which("bash")
    if not bash_exe:
        err("Local tests requested but no bash executable was found.")
        raise RuntimeError("Bash is required for local tests")

    candidates = [
        repo_root / "scripts" / "bash" / "test.sh",
        repo_root / "digital_ocean" / "scripts" / "bash" / "test.sh",
    ]
    test_script = next((c for c in candidates if c.is_file()), None)
    if not test_script:
        raise RuntimeError("Local tests script not found (bash test.sh)")

    args = [
        bash_exe,
        str(test_script),
    ]
    if env_path and test_script == (repo_root / "scripts" / "bash" / "test.sh"):
        args += ["--env-file", env_path]

    log(f"Running local tests suite via {bash_exe}...")
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    stdout_text = result.stdout or ""
    stderr_text = result.stderr or ""
    if stdout_text:
        _write_artifact_text("all-tests.json", stdout_text)
    if stderr_text:
        _write_artifact_text("all-tests.stderr.txt", stderr_text)
    if result.returncode != 0:
        raise RuntimeError(f"All-tests suite failed with exit code {result.returncode}")


def _run_all_tests_suite() -> None:
    runner = os.getenv("DEPLOY_TEST_RUNNER", "").strip().lower()
    if runner == "bash":
        _run_bash_tests_suite()
        return

    if not artifact_dir_path:
        err("Local tests requested but DEPLOY_ARTIFACT_DIR is not set.")
        raise RuntimeError("DEPLOY_ARTIFACT_DIR is required for local tests")

    ps_exe = _find_powershell_exe()
    if not ps_exe:
        err("Local tests requested but no PowerShell executable (pwsh/powershell) was found.")
        raise RuntimeError("PowerShell is required for local tests")

    test_script = repo_root / "digital_ocean" / "scripts" / "powershell" / "test.ps1"
    if not test_script.is_file():
        raise RuntimeError(f"Local tests script not found at {test_script}")

    args = [
        ps_exe,
        "-NoProfile",
    ]
    if os.path.basename(ps_exe).lower().startswith("powershell"):
        args += ["-ExecutionPolicy", "Bypass"]
    args += [
        "-File",
        str(test_script),
        "-EnvPath",
        env_path,
        "-LogsDir",
        str(artifact_dir_path),
        "-UseLatestTimestamp",
        "0",
        "-Json",
        "-All",
    ]
    domain = os.getenv("WEBSITE_DOMAIN", "").strip()
    if domain:
        args += ["-Domain", domain]
    if ip_address:
        args += ["-ResolveIp", str(ip_address), "-ExpectedIpv4", str(ip_address)]

    log(f"Running local tests suite via {ps_exe}...")
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    stdout_text = result.stdout or ""
    stderr_text = result.stderr or ""
    if stdout_text:
        _write_artifact_text("all-tests.json", stdout_text)
    if stderr_text:
        _write_artifact_text("all-tests.stderr.txt", stderr_text)
    if result.returncode != 0:
        raise RuntimeError(f"All-tests suite failed with exit code {result.returncode}")


atexit.register(_finalize_artifacts)
_init_artifacts()

stage("initialize artifacts and env")


stage("check ssh keys")
log(f"Checking for SSH key at {ssh_key_path} and {pub_key_path}")
if not os.path.exists(ssh_key_path):
    err(f"SSH key file {ssh_key_path} does not exist. Please check your key path and permissions.")
    exit(1)
if not os.path.exists(ssh_key_path) or not os.path.exists(pub_key_path):
    os.makedirs(ssh_dir, exist_ok=True)
    log(f"Generating SSH key: {ssh_key_path}")
    result = subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-f", ssh_key_path, "-N", ""],
        capture_output=True,
        text=True,
    )
    print(f"[ssh-keygen stdout]:\n{result.stdout}")
    if result.stderr:
        print(f"[ssh-keygen stderr]:\n{result.stderr}")
else:
    log(f"SSH key already exists: {ssh_key_path}")


stage("load ssh public key")
log(f"Reading public key from {pub_key_path}")
with open(pub_key_path) as f:
    pubkey = f.read().strip()
print(f"[public key]: {pubkey}")


stage("update env with ssh key")
log(f"Updating DO_API_SSH_KEYS in .env at {env_path}")
with open(env_path) as f:
    lines = f.readlines()
found = False
for i, line in enumerate(lines):
    if line.strip().startswith("DO_API_SSH_KEYS"):
        lines[i] = f"DO_API_SSH_KEYS={pubkey}\n"
        found = True
        break
if not found:
    lines.append(f"DO_API_SSH_KEYS={pubkey}\n")
with open(env_path, "w") as f:
    f.writelines(lines)
log(".env updated with public key.")
_DEPLOY_CONFIG["DO_API_SSH_KEYS"] = pubkey


# --- Recovery routine, now only called explicitly ---
def recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path):
    try:
        print("[RECOVERY] Attempting SSH recovery and diagnostics...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip_address, username=SSH_USER, key_filename=ssh_key_path)
        # Only check logs, do not rerun any scripts
        for log_path in ["/var/log/cloud-init-output.log"]:
            # Check if file exists before tailing
            stdin, stdout, stderr = ssh_client.exec_command(
                f"test -f {log_path} && echo exists || echo missing"
            )
            exists = stdout.read().decode().strip()
            if exists == "exists":
                print(f"[RECOVERY] Checking {log_path}...")
                stdin, stdout, stderr = ssh_client.exec_command(f"tail -n 100 {log_path}")
                print(stdout.read().decode())
                err_out = stderr.read().decode()
                if err_out:
                    print(f"[RECOVERY][stderr] {err_out}")
            else:
                print(f"[RECOVERY] {log_path} does not exist, skipping.")
        ssh_client.close()
    except Exception as e:
        print(f"[RECOVERY] SSH recovery failed: {e}")


DO_API_TOKEN = os.getenv("DO_API_TOKEN")
DO_DOMAIN = _expand_env_templates(os.getenv("DO_DOMAIN"), _EXPANSION_ENV)  # e.g. example.com
DO_DROPLET_NAME = _expand_env_templates(
    os.getenv("DO_DROPLET_NAME", "${PROJECT_NAME}-droplet"), _EXPANSION_ENV
)
DO_API_REGION = os.getenv("DO_API_REGION", "nyc3")
DO_API_SIZE = os.getenv("DO_API_SIZE", "s-1vcpu-1gb")
DO_API_IMAGE = os.getenv("DO_API_IMAGE", "ubuntu-22-04-x64")
PGADMIN_DNS_LABEL = os.getenv("PGADMIN_DNS_LABEL", "pgadmin").strip() or "pgadmin"
TRAEFIK_DNS_LABEL = os.getenv("TRAEFIK_DNS_LABEL", "traefik").strip() or "traefik"
DJANGO_ADMIN_DNS_LABEL = os.getenv("DJANGO_ADMIN_DNS_LABEL", "admin").strip() or "admin"
FLOWER_DNS_LABEL = os.getenv("FLOWER_DNS_LABEL", "flower").strip() or "flower"
SWAGGER_DNS_LABEL = os.getenv("SWAGGER_DNS_LABEL", "swagger").strip() or "swagger"


def ensure_dns_records_for_droplet(*, client: Client, droplet_id: int, ipv4_address: str) -> None:
    if _truthy_env(os.getenv("DO_SKIP_DNS"), default=False):
        log("Skipping DNS updates because DO_SKIP_DNS is set.")
        return
    log("Updating DNS A/AAAA records for required hostnames...")
    try:
        log_json("API Request - domains.list_records", {"domain": DO_DOMAIN})
        records = _do_api_call("domains.list_records", client.domains.list_records, DO_DOMAIN)[
            "domain_records"
        ]
        log_json("API Response - domains.list_records", records)

        ipv6_enabled = _truthy_env(os.getenv("DO_IPV6_ENABLED"), default=True)
        ipv6_wait_timeout_sec = int(
            os.getenv("DO_IPV6_WAIT_TIMEOUT", os.getenv("DO_DEPLOY_TIMEOUT", "180"))
        )

        # Refresh droplet info right before DNS changes.
        droplet_info = _do_api_call("droplets.get", client.droplets.get, int(droplet_id))["droplet"]
        ipv6_address = _get_public_ipv6(droplet_info)
        if ipv6_enabled and not ipv6_address:
            try:
                ipv6_address, droplet_info = wait_for_public_ipv6(
                    client=client,
                    droplet_id=int(droplet_id),
                    timeout_sec=ipv6_wait_timeout_sec,
                    interval_sec=5,
                )
                log(f"Droplet IPv6 assigned: {ipv6_address}")
            except Exception as e:
                err(f"IPv6 is enabled but no IPv6 address was assigned in time: {e}")
                err("Aborting DNS updates to avoid leaving stale AAAA records.")
                raise

        # Track which records exist
        found = {
            "A_root": None,
            "A_www": None,
            "AAAA_root": None,
            "A_pgadmin": None,
            "AAAA_pgadmin": None,
            "A_traefik": None,
            "AAAA_traefik": None,
            "A_django_admin": None,
            "AAAA_django_admin": None,
            "A_flower": None,
            "AAAA_flower": None,
            "A_swagger": None,
            "AAAA_swagger": None,
        }
        updated = {k: False for k in found}

        for record in records:
            # Update all A records for this domain (root, www, subdomains, wildcard)
            if record.get("type") == "A":
                name = record.get("name")
                match_a = name in (
                    "@",
                    DO_DOMAIN,
                    "",
                    "www",
                    f"www.{DO_DOMAIN}",
                    TRAEFIK_DNS_LABEL,
                    f"{TRAEFIK_DNS_LABEL}.{DO_DOMAIN}",
                    PGADMIN_DNS_LABEL,
                    f"{PGADMIN_DNS_LABEL}.{DO_DOMAIN}",
                    DJANGO_ADMIN_DNS_LABEL,
                    f"{DJANGO_ADMIN_DNS_LABEL}.{DO_DOMAIN}",
                    FLOWER_DNS_LABEL,
                    f"{FLOWER_DNS_LABEL}.{DO_DOMAIN}",
                    SWAGGER_DNS_LABEL,
                    f"{SWAGGER_DNS_LABEL}.{DO_DOMAIN}",
                )
                if isinstance(name, str):
                    match_a = match_a or DO_DOMAIN in name or name.startswith("*")
                if match_a:
                    if name in ("@", DO_DOMAIN, ""):
                        found["A_root"] = record
                        updated["A_root"] = True
                    if name in ("www", f"www.{DO_DOMAIN}"):
                        found["A_www"] = record
                        updated["A_www"] = True
                    if name in (TRAEFIK_DNS_LABEL, f"{TRAEFIK_DNS_LABEL}.{DO_DOMAIN}"):
                        found["A_traefik"] = record
                        updated["A_traefik"] = True
                    if name in (PGADMIN_DNS_LABEL, f"{PGADMIN_DNS_LABEL}.{DO_DOMAIN}"):
                        found["A_pgadmin"] = record
                        updated["A_pgadmin"] = True
                    if name in (DJANGO_ADMIN_DNS_LABEL, f"{DJANGO_ADMIN_DNS_LABEL}.{DO_DOMAIN}"):
                        found["A_django_admin"] = record
                        updated["A_django_admin"] = True
                    if name in (FLOWER_DNS_LABEL, f"{FLOWER_DNS_LABEL}.{DO_DOMAIN}"):
                        found["A_flower"] = record
                        updated["A_flower"] = True
                    if name in (SWAGGER_DNS_LABEL, f"{SWAGGER_DNS_LABEL}.{DO_DOMAIN}"):
                        found["A_swagger"] = record
                        updated["A_swagger"] = True

                    if DRY_RUN:
                        log(f"[DRY RUN] Would update A record ({name}) -> {ipv4_address}")
                    else:
                        log_json(
                            "API Request - domains.update_record (A_generic)",
                            {"id": record["id"], "data": ipv4_address},
                        )
                        resp = _do_api_call(
                            "domains.update_record (A_generic)",
                            client.domains.update_record,
                            DO_DOMAIN,
                            record["id"],
                            {
                                "type": "A",
                                "name": name,
                                "data": ipv4_address,
                            },
                        )
                        log_json("API Response - domains.update_record (A_generic)", resp)
                        log(f"Updated A record ({name}) -> {ipv4_address}")

            # Update all AAAA records for this domain (root, subdomains, wildcard)
            if record.get("type") == "AAAA":
                name = record.get("name")
                match_aaaa = name in (
                    "@",
                    DO_DOMAIN,
                    "",
                    TRAEFIK_DNS_LABEL,
                    f"{TRAEFIK_DNS_LABEL}.{DO_DOMAIN}",
                    PGADMIN_DNS_LABEL,
                    f"{PGADMIN_DNS_LABEL}.{DO_DOMAIN}",
                    DJANGO_ADMIN_DNS_LABEL,
                    f"{DJANGO_ADMIN_DNS_LABEL}.{DO_DOMAIN}",
                    FLOWER_DNS_LABEL,
                    f"{FLOWER_DNS_LABEL}.{DO_DOMAIN}",
                    SWAGGER_DNS_LABEL,
                    f"{SWAGGER_DNS_LABEL}.{DO_DOMAIN}",
                )
                if isinstance(name, str):
                    match_aaaa = match_aaaa or DO_DOMAIN in name or name.startswith("*")
                if match_aaaa:
                    if name in ("@", DO_DOMAIN, ""):
                        found["AAAA_root"] = record
                        updated["AAAA_root"] = True
                    if name in (TRAEFIK_DNS_LABEL, f"{TRAEFIK_DNS_LABEL}.{DO_DOMAIN}"):
                        found["AAAA_traefik"] = record
                        updated["AAAA_traefik"] = True
                    if name in (PGADMIN_DNS_LABEL, f"{PGADMIN_DNS_LABEL}.{DO_DOMAIN}"):
                        found["AAAA_pgadmin"] = record
                        updated["AAAA_pgadmin"] = True
                    if name in (DJANGO_ADMIN_DNS_LABEL, f"{DJANGO_ADMIN_DNS_LABEL}.{DO_DOMAIN}"):
                        found["AAAA_django_admin"] = record
                        updated["AAAA_django_admin"] = True
                    if name in (FLOWER_DNS_LABEL, f"{FLOWER_DNS_LABEL}.{DO_DOMAIN}"):
                        found["AAAA_flower"] = record
                        updated["AAAA_flower"] = True
                    if name in (SWAGGER_DNS_LABEL, f"{SWAGGER_DNS_LABEL}.{DO_DOMAIN}"):
                        found["AAAA_swagger"] = record
                        updated["AAAA_swagger"] = True

                    if ipv6_address:
                        if DRY_RUN:
                            log(f"[DRY RUN] Would update AAAA record ({name}) -> {ipv6_address}")
                        else:
                            log_json(
                                "API Request - domains.update_record (AAAA_generic)",
                                {"id": record["id"], "data": ipv6_address},
                            )
                            resp = _do_api_call(
                                "domains.update_record (AAAA_generic)",
                                client.domains.update_record,
                                DO_DOMAIN,
                                record["id"],
                                {
                                    "type": "AAAA",
                                    "name": name,
                                    "data": ipv6_address,
                                },
                            )
                            log_json("API Response - domains.update_record (AAAA_generic)", resp)
                            log(f"Updated AAAA record ({name}) -> {ipv6_address}")

        def create_a(label: str, key: str) -> None:
            if found[key]:
                return
            if DRY_RUN:
                log(f"[DRY RUN] Would create A record ({label}) -> {ipv4_address}")
                return
            log_json(
                "API Request - domains.create_record (A)",
                {"type": "A", "name": label, "data": ipv4_address},
            )
            resp = _do_api_call(
                "domains.create_record (A)",
                client.domains.create_record,
                DO_DOMAIN,
                {"type": "A", "name": label, "data": ipv4_address},
            )
            log_json("API Response - domains.create_record (A)", resp)
            log(f"Created A record ({label}) -> {ipv4_address}")

        def create_aaaa(label: str, key: str) -> None:
            if not ipv6_address or found[key]:
                return
            if DRY_RUN:
                log(f"[DRY RUN] Would create AAAA record ({label}) -> {ipv6_address}")
                return
            log_json(
                "API Request - domains.create_record (AAAA)",
                {"type": "AAAA", "name": label, "data": ipv6_address},
            )
            resp = _do_api_call(
                "domains.create_record (AAAA)",
                client.domains.create_record,
                DO_DOMAIN,
                {"type": "AAAA", "name": label, "data": ipv6_address},
            )
            log_json("API Response - domains.create_record (AAAA)", resp)
            log(f"Created AAAA record ({label}) -> {ipv6_address}")

        # Root + www + required labels
        create_a("@", "A_root")
        create_a("www", "A_www")
        create_aaaa("@", "AAAA_root")

        create_a(TRAEFIK_DNS_LABEL, "A_traefik")
        create_aaaa(TRAEFIK_DNS_LABEL, "AAAA_traefik")

        create_a(PGADMIN_DNS_LABEL, "A_pgadmin")
        create_aaaa(PGADMIN_DNS_LABEL, "AAAA_pgadmin")

        create_a(DJANGO_ADMIN_DNS_LABEL, "A_django_admin")
        create_aaaa(DJANGO_ADMIN_DNS_LABEL, "AAAA_django_admin")

        create_a(FLOWER_DNS_LABEL, "A_flower")
        create_aaaa(FLOWER_DNS_LABEL, "AAAA_flower")

        create_a(SWAGGER_DNS_LABEL, "A_swagger")
        create_aaaa(SWAGGER_DNS_LABEL, "AAAA_swagger")

        if not updated["A_root"] and not updated["A_www"] and not updated["AAAA_root"]:
            log("No A/AAAA records for root or www found to update or create.")
    except Exception as e:
        err(f"DNS update failed: {e}")
        raise


def _truthy_env(value: str, default: bool = True) -> bool:
    if value is None:
        return default
    v = str(value).strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    return default


def _get_public_ipv4(droplet: dict) -> str:
    v4_list = (droplet or {}).get("networks", {}).get("v4", []) or []
    public_v4 = next(
        (n for n in v4_list if n.get("type") == "public" and n.get("ip_address")), None
    )
    if public_v4 and public_v4.get("ip_address"):
        return public_v4["ip_address"]
    # Fall back to first v4 if present
    return (v4_list[0] if v4_list else {}).get("ip_address")


def _get_public_ipv6(droplet: dict) -> str:
    v6_list = (droplet or {}).get("networks", {}).get("v6", []) or []
    public_v6 = next(
        (n for n in v6_list if n.get("type") == "public" and n.get("ip_address")), None
    )
    if public_v6 and public_v6.get("ip_address"):
        return public_v6["ip_address"]
    # Fall back to first v6 if present
    return (v6_list[0] if v6_list else {}).get("ip_address")


def wait_for_public_ipv6(
    client: Client, droplet_id: int, timeout_sec: int, interval_sec: int = 5
) -> tuple[str, dict]:
    """Poll the Droplet until a public IPv6 address is assigned.

    Returns: (ipv6_address, droplet_info)
    Raises RuntimeError on timeout.
    """
    deadline = time.time() + max(0, int(timeout_sec))
    last_log = 0.0
    while time.time() <= deadline:
        droplet_info = client.droplets.get(droplet_id)["droplet"]
        ipv6_address = _get_public_ipv6(droplet_info)
        if ipv6_address:
            return ipv6_address, droplet_info
        now = time.time()
        if now - last_log >= 15:
            log(f"Waiting for IPv6 assignment on droplet {droplet_id}...")
            last_log = now
        time.sleep(max(1, int(interval_sec)))
    raise RuntimeError(
        f"Timed out waiting for public IPv6 on droplet {droplet_id} after {timeout_sec}s"
    )


def wait_for_public_ipv4(
    client: Client, droplet_id: int, timeout_sec: int, interval_sec: int = 5
) -> tuple[str, dict]:
    """Poll the Droplet until a public IPv4 address is assigned.

    Returns: (ipv4_address, droplet_info)
    Raises RuntimeError on timeout.
    """
    deadline = time.time() + max(0, int(timeout_sec))
    last_log = 0.0
    while time.time() <= deadline:
        droplet_info = client.droplets.get(droplet_id)["droplet"]
        ipv4_address = _get_public_ipv4(droplet_info)
        if ipv4_address:
            return ipv4_address, droplet_info
        now = time.time()
        if now - last_log >= 15:
            log(f"Waiting for IPv4 assignment on droplet {droplet_id}...")
            last_log = now
        time.sleep(max(1, int(interval_sec)))
    raise RuntimeError(
        f"Timed out waiting for public IPv4 on droplet {droplet_id} after {timeout_sec}s"
    )


# CLI flags
parser = argparse.ArgumentParser(description="Orchestrate DO deploy and post-deploy actions")
parser.add_argument("--dry-run", action="store_true", help="Print actions without making changes")
parser.add_argument(
    "--update-only",
    action="store_true",
    help="Skip droplet creation; pull latest repo on droplet and rerun post-deploy",
)
parser.add_argument(
    "--create-if-missing",
    action="store_true",
    help="Create droplet if update-only target is missing",
)
parser.add_argument(
    "--all-tests", action="store_true", help="Enable extended remote verification (celery check)"
)
parser.add_argument("--local-tests", action="store_true", help="Run local test suite after deploy")
args = parser.parse_args()
DRY_RUN = args.dry_run
UPDATE_ONLY = args.update_only
CREATE_IF_MISSING = args.create_if_missing
RUN_ALL_TESTS = args.all_tests
RUN_LOCAL_TESTS = args.local_tests
if DRY_RUN:
    print(
        "\033[1;32m[INFO]\033[0m [DRY RUN] No changes will be made. Printing planned actions only."
    )
DO_SSH_KEY_ID = os.getenv("DO_SSH_KEY_ID")
DO_API_SSH_KEYS = os.getenv("DO_API_SSH_KEYS")


log(f"DO_SSH_KEY_ID: {DO_SSH_KEY_ID}")
log(f"DO_API_SSH_KEYS: {DO_API_SSH_KEYS}")
ssh_keys = []
if DO_SSH_KEY_ID and DO_SSH_KEY_ID.strip():
    ssh_keys = [DO_SSH_KEY_ID.strip()]
elif DO_API_SSH_KEYS and DO_API_SSH_KEYS.strip():
    ssh_keys = [DO_API_SSH_KEYS.strip()]
else:
    err(
        "No valid SSH key identifier found. Set DO_SSH_KEY_ID (numeric ID or fingerprint) or DO_API_SSH_KEYS (public key string) in your .env file."
    )
    exit(1)
log(f"Using SSH keys for droplet: {ssh_keys}")
LOCAL_ENV_PATH = os.getenv(
    "LOCAL_ENV_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
)
# Remote repo path is controlled via DEPLOY_PATH/PROJECT_NAME (defaults align with deploy.ps1 remote verification)
REMOTE_ENV_PATH = _expand_env_templates(
    os.getenv("REMOTE_ENV_PATH", "/opt/apps/${PROJECT_NAME}/.env"),
    _EXPANSION_ENV,
)
SSH_USER = os.getenv("SSH_USER", "root")

client = Client(token=DO_API_TOKEN)


repo_root = Path(env_path).resolve().parent if env_path else Path(__file__).resolve().parents[3]
base_script_path = str(
    (repo_root / "digital_ocean" / "scripts" / "bash" / "digital_ocean_base.sh").resolve()
)
log(f"Loading user_data script from {base_script_path}")
with open(base_script_path) as f:
    user_data_script = f.read()

# Use the same strict, normalized configuration used by preflight and process
# setup. Do not parse the deployment file a second way.
env_dict = dict(_DEPLOY_CONFIG)
if "REPO_URL" not in env_dict or not env_dict.get("REPO_URL"):
    repo_url = env_dict.get("GIT_REPO") or env_dict.get("DO_GIT_REPO")
    if repo_url:
        env_dict["REPO_URL"] = repo_url


def substitute_env_vars(script, env):
    # Replace $VAR and ${VAR} with env[VAR] if present
    def replacer(match):
        var = match.group(1) or match.group(2)
        return env.get(var, match.group(0))

    # $VAR or ${VAR}
    pattern = re.compile(r"\$(\w+)|\${(\w+)}")
    return pattern.sub(replacer, script)


user_data_script_sub = substitute_env_vars(user_data_script, env_dict)
log("Loaded digital_ocean_base.sh for user_data (with env substitution):")
print("--- user_data script ---\n" + user_data_script_sub + "\n--- end user_data script ---")

"""DO_userdata.json location

When run via scripts/powershell/deploy.ps1 or Bash wrappers, we set DEPLOY_ARTIFACT_DIR
to a per-run folder (unknown-<timestamp>) and rename it to <ip>-<timestamp> once known.
"""


def write_do_userdata(payload: dict):
    with open(do_userdata_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    ip_address = payload.get("ip_address")
    droplet_id = payload.get("droplet_id")
    if ip_address:
        _plan_artifact_rename(ip_address)
        _apply_artifact_rename()
        if droplet_id:
            try:
                update_only = bool(UPDATE_ONLY)
            except NameError:
                update_only = False
            _write_deploy_metadata(
                droplet_id=droplet_id, ip_address=ip_address, update_only=update_only
            )


try:
    existing_userdata = {}
    if os.path.exists(do_userdata_json_path):
        with open(do_userdata_json_path, encoding="utf-8") as f:
            existing_userdata = json.load(f) or {}
except Exception:
    existing_userdata = {}

existing_userdata["user_data"] = user_data_script_sub
write_do_userdata(existing_userdata)
log("Wrote user_data to DO_userdata.json (preserving existing fields)")


def run_post_reboot() -> None:
    # --- Post-reboot configuration and service startup ---
    try:
        SSH_USER = os.getenv("SSH_USER", "root")
        deploy_root = str(env_dict.get("DEPLOY_PATH", "/opt/apps")).rstrip("/")
        project_name = str(env_dict.get("PROJECT_NAME", PROJECT_NAME)).strip("/")
        repo_path = f"{deploy_root}/{project_name}"
        log(f"Connecting via SSH to {ip_address} for post-reboot configuration...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        def ssh_connect_with_retry(max_attempts: int = 5, delay: int = 15):
            for attempt in range(1, max_attempts + 1):
                try:
                    connect_timeout = float(os.getenv("SSH_CONNECT_TIMEOUT", "30"))
                    banner_timeout = float(os.getenv("SSH_BANNER_TIMEOUT", "30"))
                    auth_timeout = float(os.getenv("SSH_AUTH_TIMEOUT", "30"))
                    ssh_client.connect(
                        ip_address,
                        username=SSH_USER,
                        key_filename=ssh_key_path,
                        timeout=connect_timeout,
                        banner_timeout=banner_timeout,
                        auth_timeout=auth_timeout,
                    )
                    return True
                except Exception as e:
                    err(f"SSH connect attempt {attempt}/{max_attempts} failed: {e}")
                    time.sleep(delay)
            return False

        def wait_for_ssh_port(host: str, port: int = 22) -> None:
            timeout_sec = int(os.getenv("SSH_PORT_TIMEOUT", "300"))
            interval_sec = int(os.getenv("SSH_PORT_INTERVAL", "5"))
            deadline = time.time() + timeout_sec
            while time.time() < deadline:
                try:
                    with socket.create_connection((host, port), timeout=5):
                        return
                except OSError:
                    time.sleep(interval_sec)
            raise RuntimeError(f"SSH port {port} did not become available within {timeout_sec}s")

        def run_ssh_cmd(
            cmd: str, label: str, *, artifact_name: str | None = None, allow_fail: bool = False
        ) -> tuple[int, str, str]:
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            out = stdout.read().decode(errors="replace") if stdout else ""
            err_out = stderr.read().decode(errors="replace") if stderr else ""
            exit_status = 0
            try:
                exit_status = stdout.channel.recv_exit_status()
            except Exception:
                exit_status = 0
            if out:
                _safe_write(out)
            if err_out:
                _safe_write(err_out, is_err=True)
            if artifact_name:
                payload = out
                if err_out:
                    payload = payload + "\n[stderr]\n" + err_out
                _write_artifact_text(artifact_name, payload)
            if exit_status != 0 and not allow_fail:
                raise RuntimeError(f"{label} failed with exit status {exit_status}")
            return exit_status, out, err_out

        def run_ssh_cmd_stream(cmd: str, label: str, *, artifact_name: str | None = None) -> None:
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            channel = stdout.channel
            stderr_started = False
            artifact_handle = None
            if artifact_name and artifact_dir_path:
                path = artifact_dir_path / artifact_name
                path.parent.mkdir(parents=True, exist_ok=True)
                artifact_handle = open(path, "w", encoding="utf-8", errors="replace")  # noqa: SIM115
            try:
                while True:
                    if channel.recv_ready():
                        chunk = channel.recv(4096).decode(errors="replace")
                        if chunk:
                            _safe_write(chunk)
                            if artifact_handle:
                                artifact_handle.write(chunk)
                                artifact_handle.flush()
                    if channel.recv_stderr_ready():
                        chunk = channel.recv_stderr(4096).decode(errors="replace")
                        if chunk:
                            if not stderr_started and artifact_handle:
                                artifact_handle.write("\n[stderr]\n")
                                artifact_handle.flush()
                                stderr_started = True
                            _safe_write(chunk, is_err=True)
                            if artifact_handle:
                                artifact_handle.write(chunk)
                                artifact_handle.flush()
                    if (
                        channel.exit_status_ready()
                        and not channel.recv_ready()
                        and not channel.recv_stderr_ready()
                    ):
                        break
                    time.sleep(0.2)
                exit_status = channel.recv_exit_status()
            finally:
                if artifact_handle:
                    artifact_handle.close()
            if exit_status != 0:
                raise RuntimeError(f"{label} failed with exit status {exit_status}")

        def download_remote_dir(remote_dir: str, local_dir: Path) -> None:
            if not artifact_dir_path:
                return
            sftp = None
            try:
                sftp = ssh_client.open_sftp()

                def _walk(rpath: str, lpath: Path) -> None:
                    try:
                        entries = sftp.listdir_attr(rpath)
                    except Exception:
                        return
                    lpath.mkdir(parents=True, exist_ok=True)
                    for entry in entries:
                        rchild = f"{rpath}/{entry.filename}"
                        lchild = lpath / entry.filename
                        if stat.S_ISDIR(entry.st_mode):
                            _walk(rchild, lchild)
                        else:
                            with suppress(Exception):
                                sftp.get(rchild, str(lchild))

                _walk(remote_dir, local_dir)
            finally:
                try:
                    if sftp:
                        sftp.close()
                except Exception:
                    pass

        try:
            droplet_status = client.droplets.get(int(droplet_id))["droplet"].get("status")
            if droplet_status and droplet_status != "active":
                log(f"Droplet status is '{droplet_status}', waiting for 'active'...")
                for _ in range(30):
                    time.sleep(5)
                    droplet_status = client.droplets.get(int(droplet_id))["droplet"].get("status")
                    if droplet_status == "active":
                        break
        except Exception as e:
            err(f"Unable to confirm droplet status before SSH: {e}")

        try:
            wait_for_ssh_port(ip_address)
        except Exception as e:
            err(str(e))

        if not ssh_connect_with_retry():
            raise RuntimeError("SSH connection failed after retries")

        # Resolve the actual repo path on the droplet (create flow uses a fixed /opt/apps/project1).
        candidates = [repo_path, f"{deploy_root}/{PROJECT_NAME}", "/opt/apps/project1"]
        candidates = [c for c in candidates if c]
        quoted = " ".join(f"'{c}'" for c in candidates)
        resolve_cmd = (
            f"for p in {quoted}; do "
            f'if [ -f "$p/development.docker.yml" ]; then echo $p; break; fi; '
            f"done"
        )
        _, resolved_out, _ = run_ssh_cmd(
            resolve_cmd, "resolve repo path", artifact_name="resolve-repo-path.txt", allow_fail=True
        )
        resolved_path = (resolved_out or "").strip().splitlines()
        if resolved_path:
            repo_path = resolved_path[-1].strip() or repo_path

        # If update-only, ensure repo exists and sync it BEFORE uploading .env.
        # Rationale:
        # - Git operations (reset/clean/checkout) can clobber local uncommitted state.
        # - We upload .env after the sync so the deployed runtime secrets/credentials win.
        if UPDATE_ONLY:
            log("[UPDATE-ONLY] Ensuring repo path exists and syncing latest changes...")
            git_remote = str(env_dict.get("GIT_REMOTE", "")).strip()
            repo_url = str(env_dict.get("REPO_URL", "")).strip()
            branch = str(env_dict.get("DO_APP_BRANCH", "main")).strip() or "main"
            if not git_remote:
                git_remote = repo_url
            if not git_remote:
                raise RuntimeError(
                    "Missing GIT_REMOTE/REPO_URL in local .env (required for --update-only repo sync)"
                )

            def sync_repo(remote_url: str) -> None:
                pull_cmd = (
                    f"set -eu; "
                    f"test -d {repo_path} || mkdir -p {repo_path}; "
                    f"cd {repo_path}; "
                    # Ensure we always have an initialized repo with a correct origin URL.
                    f"if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then "
                    f"  git remote set-url origin '{remote_url}' >/dev/null 2>&1 || true; "
                    f"else "
                    f"  git init >/dev/null 2>&1; "
                    f"  git remote remove origin >/dev/null 2>&1 || true; "
                    f"  git remote add origin '{remote_url}'; "
                    f"fi; "
                    # Fetch + hard reset to the desired branch (prefer remote branch, fall back to main).
                    f"git fetch --all --prune || true; "
                    f"TARGET='{branch}'; "
                    f"if ! git show-ref --verify --quiet \"refs/remotes/origin/$TARGET\"; then TARGET='main'; fi; "
                    f'git checkout -B "$TARGET" "origin/$TARGET" >/dev/null 2>&1 || true; '
                    f'git reset --hard "origin/$TARGET" >/dev/null 2>&1 || true; '
                    # Clean untracked files but keep ignored files (like .env). Extra exclusions are belt-and-suspenders.
                    f"git clean -fd -e .env -e '.env.*' || true"
                )
                stdin, stdout, stderr = ssh_client.exec_command(pull_cmd)
                print(stdout.read().decode())
                err_out = stderr.read().decode()
                if err_out:
                    print(err_out)

            sync_repo(git_remote)

            _, compose_check, _ = run_ssh_cmd(
                f"test -f {repo_path}/development.docker.yml && echo ok",
                "check compose file",
                artifact_name="compose-present.txt",
                allow_fail=True,
            )
            if "ok" not in (compose_check or "") and repo_url and repo_url != git_remote:
                log("Compose file missing after sync; retrying with REPO_URL...")
                sync_repo(repo_url)

        # Copy local .env to remote repo (AFTER any git sync)
        remote_env_path = f"{repo_path}/.env"
        stage("upload .env")
        log(f"Uploading .env to {remote_env_path}")
        sftp = ssh_client.open_sftp()
        sftp.put(env_path.replace("\\", "/"), remote_env_path)
        sftp.close()

        # Ensure destination folders exist for script updates.
        run_ssh_cmd(
            f"mkdir -p {repo_path}/scripts/bash {repo_path}/digital_ocean/scripts/bash "
            f"{repo_path}/digital_ocean/scripts/python {repo_path}/traefik",
            "ensure remote script dirs",
            artifact_name="ensure-dirs.txt",
            allow_fail=True,
        )

        # Push local script updates that may not exist in the remote repo yet.
        # This is required for create flows when the repo clone doesn't include newer scripts.
        stage("upload script updates")
        log("Uploading local script updates...")
        sftp = ssh_client.open_sftp()
        upload_pairs = [
            (
                str(repo_root / "scripts" / "bash" / "sync-env.sh"),
                f"{repo_path}/scripts/bash/sync-env.sh",
            ),
            (
                str(repo_root / "scripts" / "bash" / "start.sh"),
                f"{repo_path}/scripts/bash/start.sh",
            ),
            (
                str(repo_root / "scripts" / "bash" / "bootstrap-acme.sh"),
                f"{repo_path}/scripts/bash/bootstrap-acme.sh",
            ),
            (str(repo_root / "scripts" / "bash" / "test.sh"), f"{repo_path}/scripts/bash/test.sh"),
            (str(repo_root / "traefik" / "entrypoint.sh"), f"{repo_path}/traefik/entrypoint.sh"),
            (
                str(repo_root / "digital_ocean" / "scripts" / "bash" / "post_reboot_complete.sh"),
                f"{repo_path}/digital_ocean/scripts/bash/post_reboot_complete.sh",
            ),
            (
                str(repo_root / "digital_ocean" / "scripts" / "bash" / "test.sh"),
                f"{repo_path}/digital_ocean/scripts/bash/test.sh",
            ),
            (
                str(repo_root / "digital_ocean" / "scripts" / "bash" / "remote_verify_min.sh"),
                f"{repo_path}/digital_ocean/scripts/bash/remote_verify_min.sh",
            ),
            (
                str(repo_root / "digital_ocean" / "scripts" / "python" / "bootstrap_acme.py"),
                f"{repo_path}/digital_ocean/scripts/python/bootstrap_acme.py",
            ),
        ]
        for src, dest in upload_pairs:
            if os.path.isfile(src):
                log(f"Uploading {src} -> {dest}")
                sftp.put(src.replace("\\", "/"), dest)
        sftp.close()

        run_ssh_cmd(
            f"chmod +x {repo_path}/scripts/bash/*.sh {repo_path}/digital_ocean/scripts/bash/*.sh",
            "chmod scripts",
            artifact_name="chmod-scripts.txt",
            allow_fail=True,
        )

        # Run post_reboot_complete.sh to finalize config (with reconnect on drop)
        post_reboot_path = f"{repo_path}/digital_ocean/scripts/bash/post_reboot_complete.sh"
        stage("run post-reboot script")
        log(f"Running post-reboot script: {post_reboot_path}")
        try:
            run_ssh_cmd(
                f"bash {post_reboot_path}", "post-reboot script", artifact_name="post-reboot.txt"
            )
        except Exception as e:
            err(f"Post-reboot exec encountered an error: {e}. Reconnecting and retrying once...")
            ssh_client.close()
            if not ssh_connect_with_retry():
                raise RuntimeError("SSH reconnect failed after post-reboot error") from e
            run_ssh_cmd(
                f"bash {post_reboot_path}",
                "post-reboot script (retry)",
                artifact_name="post-reboot.txt",
            )

        # Start services and follow logs briefly for live visibility
        # Always rebuild to ensure latest images when updating remotely
        disable_buildkit = _truthy_env(os.getenv("DO_DISABLE_BUILDKIT"), default=False)
        buildkit_prefix = (
            "DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 " if disable_buildkit else ""
        )
        start_cmd = (
            f"cd {repo_path} && {buildkit_prefix}START_FOLLOW_LOGS=true START_BUILD_PROGRESS=plain "
            f"START_USE_DOCKER_COMPOSE_V2=true START_BUILD_TIMEOUT_SECONDS=900 "
            f"START_COMPOSE_PARALLEL_LIMIT=1 START_COMPOSE_HTTP_TIMEOUT=1200 "
            f"POST_DEPLOY_LOGS_FOLLOW_SECONDS=60 bash scripts/bash/start.sh --build --follow-logs"
        )
        stage("start services")
        log(f"Starting services: {start_cmd}")
        try:
            run_ssh_cmd_stream(start_cmd, "start services", artifact_name="start-services.txt")
        except Exception as e:
            err(f"Start services encountered an error: {e}. Reconnecting and retrying once...")
            ssh_client.close()
            if not ssh_connect_with_retry():
                raise RuntimeError("SSH reconnect failed after start error") from e
            run_ssh_cmd_stream(
                start_cmd, "start services (retry)", artifact_name="start-services.txt"
            )

        # Run full test suite after services start (update-only requested by user).
        # This is best-effort but will exit non-zero on failures.
        test_timeout = str(os.getenv("REMOTE_TEST_TIMEOUT_SECONDS", "1800"))
        test_cmd = (
            f"cd {repo_path} && "
            f"(cd react-app && NODE_OPTIONS=--max-old-space-size=1024 "
            f"npm ci --no-audit --no-fund --omit=optional --legacy-peer-deps) && "
            f"if [ -x scripts/bash/test.sh ]; then TEST_SCRIPT=scripts/bash/test.sh; "
            f"elif [ -x digital_ocean/scripts/bash/test.sh ]; then TEST_SCRIPT=digital_ocean/scripts/bash/test.sh; "
            f"else echo 'Missing test script: scripts/bash/test.sh or digital_ocean/scripts/bash/test.sh'; exit 127; fi; "
            f"timeout {test_timeout} bash $TEST_SCRIPT"
        )
        stage("run remote tests")
        log(f"Running tests: {test_cmd}")
        try:
            run_ssh_cmd(test_cmd, "remote tests", artifact_name="remote-tests.txt")
        except Exception as e:
            err(f"Test run encountered an error: {e}. Reconnecting and retrying once...")
            ssh_client.close()
            if not ssh_connect_with_retry():
                raise RuntimeError("SSH reconnect failed after test error") from e
            run_ssh_cmd(test_cmd, "remote tests (retry)", artifact_name="remote-tests.txt")

        stage("remote verify artifacts")
        log("Generating remote verification artifacts under /root/logs...")
        run_remote_verify = (
            f"cd {repo_path} && RUN_CELERY_CHECK={'1' if RUN_ALL_TESTS else '0'} "
            f"bash digital_ocean/scripts/bash/remote_verify_min.sh"
        )
        run_ssh_cmd(
            run_remote_verify, "remote verify artifacts", artifact_name="remote-verify-min.txt"
        )
        if artifact_dir_path:
            log("Downloading /root/logs into local artifacts...")
            download_remote_dir("/root/logs", artifact_dir_path / "logs")

        # Check status and logs
        def parse_ps_health(ps_text: str) -> dict[str, str]:
            summary: dict[str, str] = {}
            for line in ps_text.splitlines():
                if not line or line.startswith("NAME"):
                    continue
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) < 4:
                    # Fallback split by single spaces if columns are condensed
                    parts = line.split()
                if not parts:
                    continue
                name = parts[0]
                # STATUS column usually near the end; search for token containing health
                status_field = next(
                    (
                        p
                        for p in parts
                        if "healthy" in p.lower()
                        or "unhealthy" in p.lower()
                        or "exit" in p.lower()
                        or "restarting" in p.lower()
                    ),
                    None,
                )
                if status_field:
                    summary[name] = status_field
            return summary

        stage("collect compose status")
        log("Fetching docker compose status...")
        _, ps_output, ps_err = run_ssh_cmd(
            f"cd {repo_path} && docker compose -f development.docker.yml ps",
            "docker compose ps",
            artifact_name="compose-ps.txt",
            allow_fail=True,
        )
        if ps_err:
            ps_output = ps_output + "\n[stderr]\n" + ps_err
        health_summary = parse_ps_health(ps_output)

        def detect_http_errors(log_text: str) -> tuple[int, int, dict[str, int]]:
            errors_4xx = 0
            errors_5xx = 0
            paths: dict[str, int] = {}
            for raw_line in log_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                # Try JSON first (Traefik, structured logs)
                try:
                    obj = json.loads(line)
                    status = None
                    for key in ("status", "DownstreamStatus", "downstream_status"):
                        if key in obj:
                            status = obj[key]
                            break
                    if isinstance(status, str) and status.isdigit():
                        status = int(status)
                    if isinstance(status, int):
                        if 400 <= status <= 499:
                            errors_4xx += 1
                        elif 500 <= status <= 599:
                            errors_5xx += 1
                        # Capture path if present
                        path = obj.get("RequestPath") or obj.get("path") or obj.get("requestPath")
                        if path and (400 <= status <= 499 or 500 <= status <= 599):
                            paths[path] = paths.get(path, 0) + 1
                        continue
                except Exception:
                    pass

                # Nginx/combined log format: "GET /path HTTP/1.1" 404 ...
                m = re.search(r"\s([45]\d{2})\s", line)
                if m:
                    code = int(m.group(1))
                    if 400 <= code <= 499:
                        errors_4xx += 1
                    elif 500 <= code <= 599:
                        errors_5xx += 1
                    # Try to extract the path inside quotes
                    pm = re.search(
                        r"\"(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([^\s\"]+)\s+HTTP/", line
                    )
                    if pm:
                        p = pm.group(1)
                        if 400 <= code <= 499 or 500 <= code <= 599:
                            paths[p] = paths.get(p, 0) + 1
            return errors_4xx, errors_5xx, paths

        stage("collect service logs")
        log("Fetching key service logs (last 100 lines) and summarizing...")
        svc_errors: dict[str, dict[str, object]] = {}
        for svc in ["traefik", "nginx", "api", "django", "postgres", "pgadmin", "nginx-static"]:
            log(f"Logs for {svc}:")
            _, logs_text, logs_err = run_ssh_cmd(
                f"cd {repo_path} && docker compose -f development.docker.yml logs --tail=100 {svc}",
                f"logs {svc}",
                artifact_name=f"{svc}-logs.txt",
                allow_fail=True,
            )
            if logs_err:
                logs_text = logs_text + "\n[stderr]\n" + logs_err
            # Only perform HTTP error detection for web-facing services
            if svc in ("traefik", "nginx", "api"):
                e4, e5, paths = detect_http_errors(logs_text)
                svc_errors[svc] = {"4xx": e4, "5xx": e5, "paths": paths}

        # Print concise summary
        print("\n===== Deployment Health Summary =====")
        if health_summary:
            print("[Containers]")
            for name, status in health_summary.items():
                print(f"- {name}: {status}")
        else:
            print("[Containers] No explicit health statuses parsed.")
        if svc_errors:
            print("\n[HTTP Errors]")
            for svc, data in svc_errors.items():
                print(f"- {svc}: 4xx={data['4xx']}, 5xx={data['5xx']}")
                hotpaths = sorted(
                    ((p, c) for p, c in data.get("paths", {}).items()), key=lambda x: -x[1]
                )[:5]
                if hotpaths:
                    for p, c in hotpaths:
                        print(f"  \u2514 {p}: {c}")
        print("===== End Summary =====\n")

        ssh_client.close()
        log("Post-deploy tasks completed.")

        if RUN_LOCAL_TESTS:
            _run_all_tests_suite()
            log("Local tests suite completed.")
    except Exception as e:
        err(f"Post-deploy workflow failed: {e}")
        raise


# --- 1. Create Droplet ---

stage("prepare droplet spec")
log("Preparing droplet spec...")
droplet_spec = {
    "name": DO_DROPLET_NAME,
    "region": DO_API_REGION,
    "size": DO_API_SIZE,
    "image": DO_API_IMAGE,
    "ssh_keys": ssh_keys,
    "tags": [PROJECT_NAME],
    "user_data": user_data_script_sub,
    "ipv6": True,
}
log_json("Droplet spec being sent", droplet_spec)

# Determine droplet to use (create or reuse) and set ip_address/droplet_id/droplet_info
ip_address = None
droplet_id = None
droplet_info = None

fallback_to_create = False
if UPDATE_ONLY:
    stage("locate existing droplet")
    log("[UPDATE-ONLY] Skipping creation; locating existing droplet by name...")
    try:
        lst = client.droplets.list(per_page=200)
        matches = [d for d in lst.get("droplets", []) if d.get("name") == DO_DROPLET_NAME]
        if not matches:
            if CREATE_IF_MISSING:
                log(
                    f"[UPDATE-ONLY] No existing droplet found named {DO_DROPLET_NAME}; falling back to create."
                )
                fallback_to_create = True
            else:
                raise RuntimeError(f"No existing droplet found named {DO_DROPLET_NAME}")

        if fallback_to_create:
            UPDATE_ONLY = False
        else:
            # If multiple droplets share the same name, prefer the most recently created.
            # If created_at is missing, fall back to highest id.
            def sort_key(d):
                return (d.get("created_at") or "", int(d.get("id") or 0))

            matched = sorted(matches, key=sort_key)[-1]

            droplet_id = matched["id"]
            droplet_info = client.droplets.get(droplet_id)["droplet"]
            ip_address = _get_public_ipv4(droplet_info)
            if ip_address:
                _record_ip_early(droplet_id=droplet_id, ip_address=ip_address, update_only=True)
            if not ip_address:
                ip_address, droplet_info = wait_for_public_ipv4(
                    client,
                    droplet_id,
                    timeout_sec=IP_POLL_TIMEOUT,
                    interval_sec=IP_POLL_INTERVAL,
                )
            _record_ip_early(droplet_id=droplet_id, ip_address=ip_address, update_only=True)
            if not ip_address:
                raise RuntimeError(f"Could not determine public IPv4 for droplet {droplet_id}")
            log(f"Using existing droplet {droplet_id} at {ip_address}")

            # Update DO_userdata.json for downstream scripts (deploy.ps1 uses it as a primary source)
            try:
                do_userdata = {}
                if os.path.exists(do_userdata_json_path):
                    with open(do_userdata_json_path, encoding="utf-8") as f:
                        do_userdata = json.load(f) or {}
                do_userdata["droplet_id"] = droplet_id
                do_userdata["ip_address"] = ip_address
                write_do_userdata(do_userdata)
                log(
                    f"Updated {do_userdata_json_path} with droplet_id {droplet_id} and ip_address {ip_address}"
                )
            except Exception as e:
                err(f"Failed to update {do_userdata_json_path}: {e}")

            _plan_artifact_rename(ip_address)
            _apply_artifact_rename()
            _write_deploy_metadata(droplet_id=droplet_id, ip_address=ip_address, update_only=True)

            # Always ensure required DNS records exist/update to current droplet IP.
            # This is important in --update-only, where the droplet already exists but
            # DNS may be missing/stale (e.g., swagger subdomain).
            ensure_dns_records_for_droplet(
                client=client, droplet_id=int(droplet_id), ipv4_address=str(ip_address)
            )
    except Exception as e:
        err(f"Failed to locate existing droplet: {e}")
        exit(1)

if not UPDATE_ONLY:
    stage("create droplet")
    log("Creating droplet via DigitalOcean API...")
    try:
        log_json("API Request - droplets.create", droplet_spec)
        droplet = client.droplets.create(droplet_spec)
        log_json("API Response - droplets.create", droplet)
        droplet_id = droplet["droplet"]["id"]
        log(f"Droplet created with ID: {droplet_id}")
        try:
            droplet_info = client.droplets.get(droplet_id)["droplet"]
            ip_address = _get_public_ipv4(droplet_info)
            if ip_address:
                _record_ip_early(droplet_id=droplet_id, ip_address=ip_address, update_only=False)
            ip_address, droplet_info = wait_for_public_ipv4(
                client,
                droplet_id,
                timeout_sec=IP_POLL_TIMEOUT,
                interval_sec=IP_POLL_INTERVAL,
            )
            _record_ip_early(droplet_id=droplet_id, ip_address=ip_address, update_only=False)
        except Exception as e:
            log(f"Early IPv4 poll did not return yet: {e}")
        # Wait active and set ip
        while True:
            droplet_info = client.droplets.get(droplet_id)["droplet"]
            log_json("API Response - droplets.get", droplet_info)
            if droplet_info["status"] == "active":
                break
            time.sleep(5)
            print("...", flush=True)
        ip_address = _get_public_ipv4(droplet_info)
        if not ip_address:
            raise RuntimeError(f"Could not determine public IPv4 for droplet {droplet_id}")
        log(f"Droplet is active. IP address: {ip_address}")
        print(f"Droplet created! IP address: {ip_address}")
        # Update DO_userdata.json
        try:
            with open(do_userdata_json_path, encoding="utf-8") as f:
                do_userdata = json.load(f)
            do_userdata["droplet_id"] = droplet_id
            do_userdata["ip_address"] = ip_address
            write_do_userdata(do_userdata)
            log(
                f"Updated {do_userdata_json_path} with droplet_id {droplet_id} and ip_address {ip_address}"
            )
        except Exception as e:
            err(f"Failed to update {do_userdata_json_path}: {e}")

        _plan_artifact_rename(ip_address)
        _apply_artifact_rename()
        _write_deploy_metadata(droplet_id=droplet_id, ip_address=ip_address, update_only=False)
    except Exception as e:
        err(f"Droplet creation failed: {e}")
        exit(1)

    stage("ensure dns records")
    # Always ensure required DNS records exist/update to current droplet IP.
    try:
        ensure_dns_records_for_droplet(
            client=client, droplet_id=int(droplet_id), ipv4_address=str(ip_address)
        )
    except Exception:
        recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path)
        exit(1)

    stage("wait for ssh availability")
    log(f"Using SSH user: {SSH_USER}")
    ssh_cmd = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-i",
        ssh_key_path.replace("\\", "/"),
        f"{SSH_USER}@{ip_address}",
        "true",  # Just test connection
    ]

    # Wait for SSH to become available (initial boot)
    if not UPDATE_ONLY:
        log(
            f"Waiting {SSH_INITIAL_WAIT} seconds before first SSH availability check after droplet creation..."
        )
        time.sleep(SSH_INITIAL_WAIT)
    ssh_success = False
    for attempt in range(1, SSH_ATTEMPTS + 1):
        try:
            log(f"SSH availability check attempt {attempt}/{SSH_ATTEMPTS}...")
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=SSH_TIMEOUT,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                log("SSH is available. Proceeding to cloud-init log polling for reboot marker.")
                ssh_success = True
                SUMMARY.append(f"SSH available after {attempt} attempts.")
                break
            else:
                log(f"SSH failed: {result.stderr}")
        except Exception as e:
            log(f"SSH check exception: {e}")
        time.sleep(SSH_INTERVAL)
    if not ssh_success:
        log(
            "SSH not available after initial attempts. Proceeding to cloud-init log polling for reboot marker anyway."
        )
        SUMMARY.append("SSH not available after initial attempts.")

    # Poll cloud-init log for reboot marker BEFORE checking for SSH reboot
    ssh_log_cmd = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-i",
        ssh_key_path.replace("\\", "/"),
        f"{SSH_USER}@{ip_address}",
        "cat /var/log/cloud-init-output.log",
    ]
    log(
        f"Polling /var/log/cloud-init-output.log until completion marker '{COMPLETION_MARKER}' is found..."
    )
    completion_found = False
    cloud_init_pattern = re.compile(r"^Cloud-init v\\. .+ finished at")
    # Updated pattern: match any line containing 'Cloud-init v.' and 'finished at' (version, timestamp, and details are variable)
    cloud_init_pattern = re.compile(r"Cloud-init v\\..*finished at")
    for poll in range(1, LOG_POLL_ATTEMPTS + 1):
        try:
            result = subprocess.run(
                ssh_log_cmd,
                capture_output=True,
                text=True,
                timeout=LOG_POLL_TIMEOUT,
                encoding="utf-8",
                errors="replace",
            )
            log(f"Log poll {poll}/{LOG_POLL_ATTEMPTS}")
            log_output = result.stdout if result.stdout is not None else ""
            print("\n--- /var/log/cloud-init-output.log ---\n")
            print(log_output)
            if result.stderr:
                print(f"[stderr] {result.stderr}")
            # Look for any line matching either marker
            for line in log_output.splitlines():
                if COMPLETION_MARKER in line or cloud_init_pattern.search(line.strip()):
                    log(
                        "Cloud-init or user-data completion marker found in log. Script finished successfully."
                    )
                    print(
                        f"\n[INFO] Deployment script ran and completion marker was found.\n[DROPLET ID] {droplet_id}\n[IP ADDRESS] {ip_address}\nScript completed correctly.\n"
                    )
                    completion_found = True
                    SUMMARY.append(f"Completion marker found in log after {poll} polls.")
                    break
            if completion_found:
                break
            else:
                log("Cloud-init completion marker not found, will retry...")
        except Exception as e:
            err(f"SSH log fetch failed: {e}")
        time.sleep(LOG_POLL_INTERVAL)
    if not UPDATE_ONLY:
        if not completion_found:
            err("Did not find cloud-init completion marker in log after multiple attempts.")
            try:
                result = subprocess.run(
                    ssh_log_cmd,
                    capture_output=True,
                    text=True,
                    timeout=LOG_POLL_TIMEOUT,
                    encoding="utf-8",
                    errors="replace",
                )
                log_output = result.stdout if result.stdout is not None else ""
                print("\n--- Last 50 lines of cloud-init log ---\n")
                print("\n".join(log_output.splitlines()[-50:]))
            except Exception as e:
                err(f"Failed to fetch last lines of cloud-init log: {e}")
            recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path)
            SUMMARY.append("Cloud-init completion marker not found in log.")
            exit(1)
        log("Deployment script completed successfully.")
        SUMMARY.append("Deployment script completed successfully.")

# Extra stabilization wait to allow services/SSH to settle
STABILIZATION_WAIT = int(os.getenv("POST_DEPLOY_STABILIZATION_SECONDS", "60"))
if not UPDATE_ONLY:
    log(f"Waiting {STABILIZATION_WAIT} seconds for SSH/services to stabilize...")
    time.sleep(STABILIZATION_WAIT)

run_post_reboot()
exit(0)
