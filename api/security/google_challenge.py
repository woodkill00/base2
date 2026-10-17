"""Short-lived, one-use GIS browser binding; no provider credentials retained."""

import hashlib
import re
import secrets

from api import redis_client

TTL = 300
COOKIE = 'base2_google_challenge'
PATH = '/api/auth/oauth/google'


def _key(binding: str) -> str:
    if not isinstance(binding, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', binding):
        raise ValueError('google_challenge_rejected')
    return redis_client.key('google-challenge', hashlib.sha256(binding.encode()).hexdigest())


def issue() -> tuple[str, str]:
    binding, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    try:
        if not redis_client.get_client().set(_key(binding), nonce, ex=TTL, nx=True):
            raise RuntimeError()
    except Exception:
        raise RuntimeError('google_challenge_unavailable') from None
    return binding, nonce


def consume(binding: str) -> str:
    key = _key(binding)
    try:
        # GETDEL is atomic across workers. Any attempted exchange consumes the
        # challenge, including failed provider verification; never restore it.
        nonce = redis_client.get_client().getdel(key)
    except Exception:
        raise RuntimeError('google_challenge_unavailable') from None
    if isinstance(nonce, bytes):
        try:
            nonce = nonce.decode('ascii')
        except UnicodeDecodeError:
            raise ValueError('google_challenge_rejected') from None
    if not isinstance(nonce, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', nonce):
        raise ValueError('google_challenge_rejected')
    return nonce
