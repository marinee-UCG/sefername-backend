"""Encryption at rest for uploaded files and sensitive fields (document numbers, issuers...).

One master key (DATA_ENCRYPTION_KEY), AES-256-GCM. Every value is also bound to its owner:
the user id goes in as "associated data", so a value stored for user 5 only opens as user 5's.
If a bug ever put user 5's passport number on user 7's screen, it would fail to open instead
of leaking. Sharing with an employer later works the same way: the server opens a value with
its owner's id, only while the owner's permission is valid.

Not hashing: a hash cannot be turned back, so the user could not see their own number and
could never share it. Encryption can be opened again, but only with the key.
"""
import base64
import json
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

NONCE_SIZE = 12          # 96 bits, the size GCM is designed for; a fresh random one for every value
FILE_MAGIC = b"SFE1"     # encrypted file:  FILE_MAGIC | nonce | ciphertext + tag
FIELD_PREFIX = "v1."     # encrypted field: "v1." + base64(nonce | ciphertext + tag)


class DecryptError(Exception):
    """None of the configured keys opens it: wrong or lost key, damaged data, or another user's value."""


@lru_cache(maxsize=1)
def _ciphers() -> tuple[AESGCM, ...]:
    """The current key first (used to encrypt), then older keys (only to decrypt)."""
    keys = [settings.data_encryption_key, *settings.data_encryption_old_keys]
    return tuple(AESGCM(base64.urlsafe_b64decode(key)) for key in keys)


def _owner(user_id: int) -> bytes:
    return f"user:{user_id}".encode()


def _encrypt(plain: bytes, user_id: int) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    return nonce + _ciphers()[0].encrypt(nonce, plain, _owner(user_id))


def _decrypt(sealed: bytes, user_id: int) -> bytes:
    nonce, ciphertext = sealed[:NONCE_SIZE], sealed[NONCE_SIZE:]
    for cipher in _ciphers():
        try:
            return cipher.decrypt(nonce, ciphertext, _owner(user_id))
        except InvalidTag:
            continue
    raise DecryptError


def opens_with_current_key(sealed: bytes, user_id: int) -> bool:
    """For the re-encrypt scripts: is this already under the newest key?"""
    try:
        _ciphers()[0].decrypt(sealed[:NONCE_SIZE], sealed[NONCE_SIZE:], _owner(user_id))
        return True
    except InvalidTag:
        return False


# ---------- files ----------

def encrypt_bytes(content: bytes, user_id: int) -> bytes:
    return FILE_MAGIC + _encrypt(content, user_id)


def is_encrypted_file(blob: bytes) -> bool:
    return blob.startswith(FILE_MAGIC)


def decrypt_bytes(blob: bytes, user_id: int) -> bytes:
    # Files saved before encryption are returned as they are (PDF/JPG/PNG never start with FILE_MAGIC)
    if not is_encrypted_file(blob):
        return blob
    return _decrypt(blob[len(FILE_MAGIC):], user_id)


# ---------- fields ----------

def seal(value: str | None, user_id: int) -> str | None:
    """Text to store in the database. None stays None: "no number entered" is not a secret."""
    if value is None:
        return None
    return FIELD_PREFIX + base64.b64encode(_encrypt(value.encode(), user_id)).decode()


def is_sealed(value: str | None) -> bool:
    return value is not None and value.startswith(FIELD_PREFIX)


def open_sealed(value: str | None, user_id: int) -> str | None:
    """The original text. Values stored before encryption (no "v1." prefix) are returned as they are,
    until app/scripts/seal_fields.py has sealed them."""
    if value is None or not is_sealed(value):
        return value
    return _decrypt(base64.b64decode(value[len(FIELD_PREFIX):]), user_id).decode()


def seal_json(data: dict | None, user_id: int) -> str | None:
    return None if data is None else seal(json.dumps(data, ensure_ascii=False), user_id)


def open_json(value: str | None, user_id: int) -> dict | None:
    text = open_sealed(value, user_id)
    return None if text is None else json.loads(text)
