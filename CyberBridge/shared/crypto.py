"""
CyberBridge - Shared Cryptography Utilities
Provides symmetric encryption (Fernet/AES) for securing RPC payloads.
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet


# Pre-shared passphrase — change before deployment
_PASSPHRASE = b"CyberBridge_2024_SecureKey_Trading"


def _derive_key(passphrase: bytes) -> bytes:
    """Derives a 32-byte Fernet key from an arbitrary passphrase."""
    digest = hashlib.sha256(passphrase).digest()
    return base64.urlsafe_b64encode(digest)


def get_cipher() -> Fernet:
    """Returns a Fernet cipher instance using the shared passphrase."""
    return Fernet(_derive_key(_PASSPHRASE))


def encrypt(data: bytes) -> bytes:
    """Encrypts bytes using Fernet symmetric encryption."""
    return get_cipher().encrypt(data)


def decrypt(token: bytes) -> bytes:
    """Decrypts a Fernet token."""
    return get_cipher().decrypt(token)


def encrypt_str(text: str) -> str:
    """Encrypts a string and returns a base64 string token."""
    return encrypt(text.encode()).decode()


def decrypt_str(token: str) -> str:
    """Decrypts a base64 string token and returns the original string."""
    return decrypt(token.encode()).decode()
