"""
CyberBridge - Shared Cryptography Utilities
Provides symmetric encryption (Fernet/AES) for securing RPC payloads.
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet


# ─── Passphrase ───────────────────────────────────────────────────────────────
# Reads the shared secret from the CYBERBRIDGE_KEY environment variable.
# Falls back to a default value ONLY for development/testing.
# ⚠  For production, ALWAYS set the CYBERBRIDGE_KEY env var on both
#    the server machine and in the client build environment.
_PASSPHRASE = os.environ.get(
    "CYBERBRIDGE_KEY", "CyberBridge_2024_SecureKey_Trading"
).encode()

# ─── Token TTL (seconds) ─────────────────────────────────────────────────────
# Maximum age allowed for an encrypted token before it is rejected.
# Protects against replay attacks: an intercepted packet older than
# DEFAULT_TTL seconds will be automatically discarded.
DEFAULT_TTL = 60


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


def decrypt(token: bytes, ttl: int = DEFAULT_TTL) -> bytes:
    """Decrypts a Fernet token.

    Args:
        token: The encrypted Fernet token.
        ttl:   Maximum age in seconds. Tokens older than this are rejected
               to prevent replay attacks. Set to None to disable.
    """
    return get_cipher().decrypt(token, ttl=ttl)


def encrypt_str(text: str) -> str:
    """Encrypts a string and returns a base64 string token."""
    return encrypt(text.encode()).decode()


def decrypt_str(token: str, ttl: int = DEFAULT_TTL) -> str:
    """Decrypts a base64 string token and returns the original string.

    Args:
        token: The encrypted base64 string token.
        ttl:   Maximum age in seconds. Tokens older than this are rejected
               to prevent replay attacks. Set to None to disable.
    """
    return decrypt(token.encode(), ttl=ttl).decode()
