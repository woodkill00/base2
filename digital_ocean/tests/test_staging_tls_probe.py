import socket
import ssl
import threading
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from digital_ocean.scripts.python import staging_tls_probe


def _write_test_chain(tmp_path, *, san="preview.example.test", validity="valid", stem="tls"):
    now = datetime.now(UTC)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"{stem} root")])
    root = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now + timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(root_key, hashes.SHA256())
    )
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    if validity == "expired":
        not_before, not_after = now - timedelta(days=3), now - timedelta(days=1)
    elif validity == "future":
        not_before, not_after = now + timedelta(days=1), now + timedelta(days=3)
    else:
        not_before, not_after = now - timedelta(hours=1), now + timedelta(days=1)
    leaf = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, san)]))
        .issuer_name(root_name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(san)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(root_key, hashes.SHA256())
    )
    ca_path = tmp_path / f"{stem}-ca.pem"
    cert_path = tmp_path / f"{stem}-cert.pem"
    key_path = tmp_path / f"{stem}-key.pem"
    ca_path.write_bytes(root.public_bytes(serialization.Encoding.PEM))
    cert_path.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        leaf_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return ca_path, cert_path, key_path


def _serve_once(cert_path, key_path):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    def serve():
        with listener:
            connection, _ = listener.accept()
            with (
                connection,
                suppress(OSError, ssl.SSLError),
                context.wrap_socket(connection, server_side=True),
            ):
                pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return port, thread


def test_real_pinned_chain_and_hostname_succeeds(tmp_path):
    ca_path, cert_path, key_path = _write_test_chain(tmp_path)
    port, thread = _serve_once(cert_path, key_path)
    assert staging_tls_probe.verify_host(
        hostname="preview.example.test",
        connect_ip="127.0.0.1",
        port=port,
        ca_file=ca_path,
        timeout=2,
    ) == ("preview.example.test",)
    thread.join(timeout=2)


@pytest.mark.parametrize(
    "san,validity,hostname",
    (
        ("other.example.test", "valid", "preview.example.test"),
        ("preview.example.test", "expired", "preview.example.test"),
        ("preview.example.test", "future", "preview.example.test"),
    ),
)
def test_real_wrong_hostname_and_time_invalid_certificates_fail(tmp_path, san, validity, hostname):
    ca_path, cert_path, key_path = _write_test_chain(
        tmp_path, san=san, validity=validity, stem=validity + san.split(".")[0]
    )
    port, thread = _serve_once(cert_path, key_path)
    with pytest.raises(ssl.SSLCertVerificationError):
        staging_tls_probe.verify_host(
            hostname=hostname,
            connect_ip="127.0.0.1",
            port=port,
            ca_file=ca_path,
            timeout=2,
        )
    thread.join(timeout=2)


def test_real_wrong_root_and_transport_failure_are_terminal(tmp_path):
    _, cert_path, key_path = _write_test_chain(tmp_path, stem="server")
    wrong_ca, _, _ = _write_test_chain(tmp_path, stem="wrong")
    port, thread = _serve_once(cert_path, key_path)
    with pytest.raises(ssl.SSLCertVerificationError):
        staging_tls_probe.verify_host(
            hostname="preview.example.test",
            connect_ip="127.0.0.1",
            port=port,
            ca_file=wrong_ca,
            timeout=2,
        )
    thread.join(timeout=2)

    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    closed_port = closed.getsockname()[1]
    closed.close()
    with pytest.raises(OSError):
        staging_tls_probe.verify_host(
            hostname="preview.example.test",
            connect_ip="127.0.0.1",
            port=closed_port,
            ca_file=wrong_ca,
            timeout=0.2,
        )


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
