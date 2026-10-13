"""Provider dependency compatibility without real credentials or requests."""

import base64
import hashlib
import hmac
from unittest.mock import patch

from oauthlib.oauth2.rfc6749.grant_types import authorization_code
from requests_oauthlib import OAuth2Session


def test_pkce_comparisons_use_constant_time_primitive():
    verifier = "synthetic-pkce-regression-verifier-not-a-secret"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    with patch.object(authorization_code.hmac, "compare_digest", wraps=hmac.compare_digest) as compare:
        assert authorization_code.code_challenge_method_plain(verifier, verifier)
        assert not authorization_code.code_challenge_method_plain(verifier, "wrong")
        assert authorization_code.code_challenge_method_s256(verifier, challenge)
        assert not authorization_code.code_challenge_method_s256(verifier, "wrong")
        assert compare.call_count == 4


def test_oauth_client_request_composition_stays_compatible():
    session = OAuth2Session(client_id="synthetic-client", redirect_uri="https://example.test/callback")
    url, state = session.authorization_url("https://example.test/authorize", state="synthetic-state")
    assert state == "synthetic-state"
    assert "response_type=code" in url
    assert "client_id=synthetic-client" in url
