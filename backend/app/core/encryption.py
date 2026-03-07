"""Encryption utilities for sensitive data (messenger credentials, etc.)."""
import base64
import json
import os
from cryptography.fernet import Fernet
from app.config import get_settings


def _get_fernet_key() -> bytes:
    """Derive Fernet key from JWT_SECRET_KEY (deterministic, 32-byte base64url)."""
    settings = get_settings()
    secret = settings.JWT_SECRET_KEY.encode("utf-8")
    # Pad / truncate to exactly 32 bytes, then base64url-encode for Fernet
    key_bytes = (secret * 2)[:32]
    return base64.urlsafe_b64encode(key_bytes)


_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_fernet_key())
    return _fernet


def encrypt_dict(data: dict) -> str:
    """Encrypt a dict to a base64 string."""
    plaintext = json.dumps(data).encode("utf-8")
    return _get_fernet().encrypt(plaintext).decode("utf-8")


def decrypt_dict(token: str) -> dict:
    """Decrypt a base64 string back to a dict."""
    plaintext = _get_fernet().decrypt(token.encode("utf-8"))
    return json.loads(plaintext.decode("utf-8"))
