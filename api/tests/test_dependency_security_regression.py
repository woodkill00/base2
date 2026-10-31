"""Security-patch floors and small decoder regressions; no network required."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from pyasn1.codec.ber import decoder as ber
from pyasn1.codec.cer import decoder as cer
from pyasn1.type import univ

ROOT = Path(__file__).resolve().parents[2]


def pinned_versions(filename):
    return dict(re.findall(r"^([\w-]+)==([\d.]+)", (ROOT / filename).read_text(), re.M))


@pytest.mark.parametrize("filename", ("api/requirements.in", "api/requirements.txt"))
@pytest.mark.parametrize(("name", "minimum"), (("pyasn1", (0, 6, 5)), ("pypdf", (6, 21, 4))))
def test_api_decoder_security_patch_floor(filename, name, minimum):
    # CVE-2026-119194..119197 and CVE-2026-119203..119209.
    version = pinned_versions(filename)[name]
    assert tuple(map(int, version.split("."))) >= minimum


def test_media_decoder_lock_remains_closed_hashed_and_matches_api():
    filename = "api/requirements-media-inspector.txt"
    pins = pinned_versions(filename)
    assert set(pins) == {"cffi", "cryptography", "pillow", "pycparser", "pypdf"}
    assert pins["pypdf"] == pinned_versions("api/requirements.txt")["pypdf"]
    text = (ROOT / filename).read_text()
    declaration = r"^([\w-]+)==([\d.]+) \\\n    --hash=sha256:([a-f0-9]{64})$"
    entries = re.findall(declaration, text, re.M)
    assert len(entries) == len(pins)
    # Do not let an extra unpinned dependency, URL, or index option evade the allowlist.
    uncommented = re.sub(r"^#.*$", "", text, flags=re.M)
    assert not re.sub(declaration, "", uncommented, flags=re.M).strip()
    # Official 6.21.4 wheel bytes independently checked against PyPI JSON.
    if pins["pypdf"] == "6.21.4":
        assert next(digest for name, _, digest in entries if name == "pypdf") == (
            "33e4fb41ca352810eb4e9838aa0d82d6888a5f8bf682f43e99cce5faa666255c"
        )


@pytest.mark.parametrize("decoder", (ber, cer))
def test_nested_asn1_octet_fragments_decode_to_values_not_encoded_tlv(decoder):
    # The 0.6.5 linear-time fragment reassembly also repairs nested fragments.
    # This tiny BER encoding previously returned the inner tag/length as data.
    value, remainder = decoder.decode(
        b"\x24\x0a\x24\x04\x04\x02AB\x04\x02CD", asn1Spec=univ.OctetString()
    )
    assert bytes(value) == b"ABCD"
    assert remainder == b""


def test_pdf_missing_xref_trailer_fails_instead_of_looping():
    # CVE-2026-119203 / upstream py-pdf/pypdf#4289. A subprocess timeout
    # makes a regressed dependency fail the test rather than hang the suite.
    probe = r'''
from io import BytesIO
from pypdf import PdfReader
from pypdf.errors import PdfReadError

data = b"%PDF-1.4\nstartxref\n28\n%%EOF\nxref\n1 0\naaa"
try:
    PdfReader(BytesIO(data))
except PdfReadError as error:
    assert "Xref parsing stuck" in str(error), str(error)
else:
    raise AssertionError("malformed PDF unexpectedly accepted")
'''
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, timeout=10, check=False
    )
    assert result.returncode == 0, result.stderr
