import os
import sys
import socket
import subprocess
import time
from shutil import which

import httpx
import pytest


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_gunicorn_serves_health() -> None:
    if sys.platform.startswith("win"):
        pytest.skip("gunicorn not supported on Windows (fcntl missing)")
    if which("gunicorn") is None:
        pytest.skip("gunicorn not available on PATH")

    port = _get_free_port()
    env = os.environ.copy()

    cmd = [
        "gunicorn",
        "api.main:app",
        "-k",
        "uvicorn.workers.UvicornWorker",
        "--bind",
        f"127.0.0.1:{port}",
        "--workers",
        "1",
        "--timeout",
        "30",
        "--graceful-timeout",
        "5",
    ]

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        url = f"http://127.0.0.1:{port}/api/health"
        deadline = time.time() + 20
        last_error: Exception | None = None

        while time.time() < deadline:
            if proc.poll() is not None:
                out, _ = proc.communicate(timeout=2)
                raise AssertionError(
                    "gunicorn exited before becoming ready\n\n"
                    f"exit_code={proc.returncode}\n\n"
                    f"output:\n{out}"
                )

            try:
                with httpx.Client(timeout=1.0) as client:
                    r = client.get(url)
                if r.status_code == 200:
                    return
            except Exception as e:  # noqa: BLE001
                last_error = e

            time.sleep(0.25)

        out = ""
        if proc.stdout is not None:
            try:
                out = proc.stdout.read()
            except Exception:
                out = ""

        raise AssertionError(
            "gunicorn did not become ready within 20s\n"
            f"last_error={last_error!r}\n\n"
            f"partial_output:\n{out}"
        )
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
