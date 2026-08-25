import pytest
from cryptography.fernet import Fernet

from api.security.secret_box import SecretBox, SecretBoxError


def test_secret_box_round_trip_and_randomized_ciphertext():
    box = SecretBox(Fernet.generate_key().decode('ascii'))
    first = box.encrypt('totp-secret')
    second = box.encrypt('totp-secret')
    assert first != second
    assert box.decrypt(first) == box.decrypt(second) == 'totp-secret'


@pytest.mark.parametrize('key', ('', 'not-a-fernet-key'))
def test_secret_box_rejects_invalid_keys(key):
    with pytest.raises(SecretBoxError, match='identity_encryption_key_invalid'):
        SecretBox(key)


def test_secret_box_rejects_empty_plaintext_and_tampering():
    box = SecretBox(Fernet.generate_key().decode('ascii'))
    with pytest.raises(SecretBoxError, match='secret_required'):
        box.encrypt('')
    with pytest.raises(SecretBoxError, match='secret_integrity_failed'):
        box.decrypt('tampered')
