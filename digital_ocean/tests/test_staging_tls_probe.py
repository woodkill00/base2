import ssl

import pytest

from digital_ocean.scripts.python import staging_tls_probe


class _Socket:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def getpeercert(self):
        return {"subjectAltName": (("DNS", "preview.example.test"),)}


class _Context:
    verify_mode = ssl.CERT_REQUIRED
    check_hostname = True

    def __init__(self, *, failure=None):
        self.failure = failure
        self.hostname = None

    def wrap_socket(self, raw, *, server_hostname):
        self.hostname = server_hostname
        if self.failure:
            raise self.failure
        if server_hostname != "preview.example.test":
            raise ssl.CertificateError("hostname mismatch")
        return raw


def test_verified_staging_connection_requires_pinned_ca_and_hostname(tmp_path, monkeypatch):
    ca_file = tmp_path / "staging.pem"
    ca_file.write_text("test-only trust anchor", encoding="utf-8")
    context = _Context()
    observed = {}

    def create_context(*, cafile):
        observed["cafile"] = cafile
        return context

    monkeypatch.setattr(staging_tls_probe.ssl, "create_default_context", create_context)
    monkeypatch.setattr(staging_tls_probe.socket, "create_connection", lambda *_a, **_k: _Socket())
    sans = staging_tls_probe.verify_host(
        hostname="preview.example.test",
        connect_ip="127.0.0.1",
        port=443,
        ca_file=ca_file,
        timeout=1,
    )
    assert sans == ("preview.example.test",)
    assert observed == {"cafile": str(ca_file)}
    assert context.hostname == "preview.example.test"


@pytest.mark.parametrize(
    "hostname,failure",
    [
        ("wrong.example.test", None),
        (
            "preview.example.test",
            ssl.SSLCertVerificationError("untrusted or expired certificate"),
        ),
    ],
)
def test_wrong_host_untrusted_and_expired_chains_fail_closed(
    tmp_path, monkeypatch, hostname, failure
):
    ca_file = tmp_path / "staging.pem"
    ca_file.write_text("test-only trust anchor", encoding="utf-8")
    monkeypatch.setattr(
        staging_tls_probe.ssl,
        "create_default_context",
        lambda **_kwargs: _Context(failure=failure),
    )
    monkeypatch.setattr(staging_tls_probe.socket, "create_connection", lambda *_a, **_k: _Socket())
    with pytest.raises((ssl.CertificateError, ssl.SSLCertVerificationError)):
        staging_tls_probe.verify_host(
            hostname=hostname,
            connect_ip="127.0.0.1",
            port=443,
            ca_file=ca_file,
            timeout=1,
        )


def test_missing_trust_store_fails_before_network(tmp_path):
    with pytest.raises(staging_tls_probe.StagingTLSProbeError, match="trust_store_missing"):
        staging_tls_probe.verify_host(
            hostname="preview.example.test",
            connect_ip="127.0.0.1",
            port=443,
            ca_file=tmp_path / "missing.pem",
            timeout=1,
        )


def test_rejects_a_context_that_disables_verification(tmp_path, monkeypatch):
    ca_file = tmp_path / "staging.pem"
    ca_file.write_text("test-only trust anchor", encoding="utf-8")
    context = _Context()
    context.check_hostname = False
    monkeypatch.setattr(staging_tls_probe.ssl, "create_default_context", lambda **_kwargs: context)
    with pytest.raises(staging_tls_probe.StagingTLSProbeError, match="verification_disabled"):
        staging_tls_probe.verify_host(
            hostname="preview.example.test",
            connect_ip="127.0.0.1",
            port=443,
            ca_file=ca_file,
            timeout=1,
        )


def test_rejects_a_certificate_without_dns_sans(tmp_path, monkeypatch):
    ca_file = tmp_path / "staging.pem"
    ca_file.write_text("test-only trust anchor", encoding="utf-8")
    socket_without_sans = _Socket()
    socket_without_sans.getpeercert = lambda: {"subjectAltName": (("IP Address", "127.0.0.1"),)}
    monkeypatch.setattr(
        staging_tls_probe.ssl, "create_default_context", lambda **_kwargs: _Context()
    )
    monkeypatch.setattr(
        staging_tls_probe.socket, "create_connection", lambda *_a, **_k: socket_without_sans
    )
    with pytest.raises(staging_tls_probe.StagingTLSProbeError, match="dns_san_missing"):
        staging_tls_probe.verify_host(
            hostname="preview.example.test",
            connect_ip="127.0.0.1",
            port=443,
            ca_file=ca_file,
            timeout=1,
        )


def test_wait_retries_a_host_then_returns_verified_sans(tmp_path, monkeypatch):
    attempts = []

    def verify(**kwargs):
        attempts.append(kwargs["hostname"])
        if len(attempts) == 1:
            raise OSError("not ready")
        return (kwargs["hostname"],)

    ticks = iter([0.0, 0.1, 0.2])
    monkeypatch.setattr(staging_tls_probe.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(staging_tls_probe.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(staging_tls_probe, "verify_host", verify)
    result = staging_tls_probe.wait_for_hosts(
        hosts=["preview.example.test"],
        connect_ip="127.0.0.1",
        port=443,
        ca_file=tmp_path / "unused.pem",
        wait_seconds=10,
        retry_seconds=0,
    )
    assert result == {"preview.example.test": ("preview.example.test",)}
    assert attempts == ["preview.example.test", "preview.example.test"]


def test_wait_expiry_reports_only_safe_error_types(tmp_path, monkeypatch):
    ticks = iter([0.0, 0.1, 1.1])
    monkeypatch.setattr(staging_tls_probe.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(staging_tls_probe.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        staging_tls_probe,
        "verify_host",
        lambda **_kwargs: (_ for _ in ()).throw(ssl.SSLError("sensitive detail")),
    )
    with pytest.raises(
        staging_tls_probe.StagingTLSProbeError,
        match="staging_tls_wait_expired:preview.example.test:SSLError",
    ):
        staging_tls_probe.wait_for_hosts(
            hosts=["preview.example.test"],
            connect_ip="127.0.0.1",
            port=443,
            ca_file=tmp_path / "unused.pem",
            wait_seconds=1,
            retry_seconds=0,
        )


def test_cli_reports_success_and_bounded_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        staging_tls_probe,
        "wait_for_hosts",
        lambda **_kwargs: {"preview.example.test": ("preview.example.test",)},
    )
    args = [
        "--ca-file",
        str(tmp_path / "ca.pem"),
        "--connect-ip",
        "127.0.0.1",
        "--hosts",
        "preview.example.test",
    ]
    assert staging_tls_probe.main(args) == 0
    assert "OK: preview.example.test verified" in capsys.readouterr().out
    monkeypatch.setattr(
        staging_tls_probe,
        "wait_for_hosts",
        lambda **_kwargs: (_ for _ in ()).throw(
            staging_tls_probe.StagingTLSProbeError("bounded_failure")
        ),
    )
    assert staging_tls_probe.main(args) == 2
    assert capsys.readouterr().out == "ERROR: bounded_failure\n"
