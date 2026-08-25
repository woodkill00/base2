from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class SecretBoxError(ValueError):
    pass


class SecretBox:
    def __init__(self, key: str):
        try:
            self._fernet = Fernet(key.encode('ascii'))
        except Exception as exc:
            raise SecretBoxError('identity_encryption_key_invalid') from exc

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            raise SecretBoxError('secret_required')
        return self._fernet.encrypt(plaintext.encode('utf-8')).decode('ascii')

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode('ascii')).decode('utf-8')
        except (InvalidToken, UnicodeError, ValueError) as exc:
            raise SecretBoxError('secret_integrity_failed') from exc

