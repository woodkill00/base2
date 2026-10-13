"""Claims verification must not inherit disabled checks from an earlier peek."""

import jwt
import pytest


@pytest.mark.parametrize("method", ["decode", "decode_complete"])
def test_jwt_options_remain_private_and_expired_claim_is_rejected(method):
    secret = "synthetic-dependency-regression-key-not-a-credential"
    token = jwt.encode({"sub": "fixture", "exp": 1}, secret, algorithm="HS256")
    options = {"verify_signature": False}
    decode = getattr(jwt, method)
    decode(token, options=options)
    assert options == {"verify_signature": False}
    options["verify_signature"] = True
    with pytest.raises(jwt.ExpiredSignatureError):
        decode(token, secret, algorithms=["HS256"], options=options)
