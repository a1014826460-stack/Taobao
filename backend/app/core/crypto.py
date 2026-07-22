from base64 import urlsafe_b64decode, urlsafe_b64encode
from os import urandom

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _key(value: str) -> bytes:
    try:
        key = urlsafe_b64decode(value.encode("ascii"))
    except Exception as exc:
        raise ValueError("CREDENTIAL_ENCRYPTION_KEY must be base64 encoded") from exc
    if len(key) != 32:
        raise ValueError("CREDENTIAL_ENCRYPTION_KEY must contain 32 bytes")
    return key


def encrypt_secret(value: str, encoded_key: str) -> str:
    nonce = urandom(12)
    ciphertext = AESGCM(_key(encoded_key)).encrypt(nonce, value.encode("utf-8"), None)
    return urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_secret(value: str, encoded_key: str) -> str:
    raw = urlsafe_b64decode(value.encode("ascii"))
    if len(raw) < 29:
        raise ValueError("Encrypted secret is malformed")
    return AESGCM(_key(encoded_key)).decrypt(raw[:12], raw[12:], None).decode("utf-8")
