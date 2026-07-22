from base64 import b64encode
from os import urandom

from backend.app.core.crypto import decrypt_secret, encrypt_secret


def test_aes_gcm_uses_fresh_nonce():
    key = b64encode(urandom(32)).decode("ascii")
    first = encrypt_secret("cookie=value", key)
    second = encrypt_secret("cookie=value", key)

    assert first != second
    assert decrypt_secret(first, key) == "cookie=value"
