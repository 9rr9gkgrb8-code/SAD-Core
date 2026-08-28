"""Portable passphrase encryption for SAD disaster-recovery backups.

The cipher implementation is delegated to PyCA cryptography's AESGCM primitive. SAD uses
PBKDF2-HMAC-SHA256 only for deriving a backup key from the operator passphrase and stores
no passphrase or derived key.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import os


CRYPTOGRAPHY_PIN = "50.0.1"
PORTABLE_MAGIC = b"SAD-PORTABLE-BACKUP\x00\x01\n"
PORTABLE_SCHEME = "portable-passphrase-aes256gcm-v1"
PORTABLE_KDF_ITERATIONS = 600_000
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32
MAX_PASSPHRASE_CHARS = 1024
MIN_PASSPHRASE_CHARS = 16


def _aesgcm_class():
    try:
        installed = importlib.metadata.version("cryptography")
    except importlib.metadata.PackageNotFoundError as error:
        raise OSError(
            "Portable SAD backup encryption requires the pinned cryptography package. "
            "Install requirements.txt first."
        ) from error
    if installed != CRYPTOGRAPHY_PIN:
        raise OSError(
            f"Portable SAD backup encryption requires cryptography=={CRYPTOGRAPHY_PIN}; found {installed}."
        )
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM


def portable_crypto_status():
    try:
        _aesgcm_class()
        return {"available": True, "version": CRYPTOGRAPHY_PIN, "scheme": PORTABLE_SCHEME}
    except OSError as error:
        return {"available": False, "version": None, "scheme": PORTABLE_SCHEME, "error": str(error)}


def _passphrase_bytes(passphrase):
    if not isinstance(passphrase, str):
        raise ValueError("Portable backup passphrase must be text.")
    if not MIN_PASSPHRASE_CHARS <= len(passphrase) <= MAX_PASSPHRASE_CHARS:
        raise ValueError(
            f"Portable backup passphrase must be {MIN_PASSPHRASE_CHARS}-{MAX_PASSPHRASE_CHARS} characters."
        )
    return passphrase.encode("utf-8")


def _key(passphrase, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", _passphrase_bytes(passphrase), salt, PORTABLE_KDF_ITERATIONS, dklen=KEY_BYTES
    )


def encrypt_portable(data, passphrase):
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("Portable backup payload must be bytes-like.")
    AESGCM = _aesgcm_class()
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    iterations = PORTABLE_KDF_ITERATIONS.to_bytes(4, "big")
    header = PORTABLE_MAGIC + salt + nonce + iterations
    cipher = AESGCM(_key(passphrase, salt))
    ciphertext = cipher.encrypt(nonce, bytes(data), header)
    return header + ciphertext


def decrypt_portable(data, passphrase):
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("Portable backup payload must be bytes-like.")
    raw = bytes(data)
    header_size = len(PORTABLE_MAGIC) + SALT_BYTES + NONCE_BYTES + 4
    if len(raw) <= header_size or not raw.startswith(PORTABLE_MAGIC):
        raise ValueError("Portable SAD backup header is missing or invalid.")
    offset = len(PORTABLE_MAGIC)
    salt = raw[offset:offset + SALT_BYTES]
    offset += SALT_BYTES
    nonce = raw[offset:offset + NONCE_BYTES]
    offset += NONCE_BYTES
    iterations = int.from_bytes(raw[offset:offset + 4], "big")
    if iterations != PORTABLE_KDF_ITERATIONS:
        raise ValueError("Portable SAD backup KDF parameters are unsupported.")
    header = raw[:header_size]
    ciphertext = raw[header_size:]
    AESGCM = _aesgcm_class()
    try:
        return AESGCM(_key(passphrase, salt)).decrypt(nonce, ciphertext, header)
    except Exception as error:
        # AESGCM raises InvalidTag for wrong passphrases or tampering. Do not distinguish
        # them to callers because both mean the container is unusable/untrusted.
        raise ValueError("Portable SAD backup passphrase is wrong or the container was tampered with.") from error
