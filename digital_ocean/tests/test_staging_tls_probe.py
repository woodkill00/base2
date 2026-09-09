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
