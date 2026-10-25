"""Security primitives: password hashing, tokens, OTP, TOTP, encryption, phones."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime
from typing import Final

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2)

# Small, deliberately modest blocklist: full breach lists belong in a vetted service.
_COMMON_PASSWORDS: Final = {
    "password",
    "password1",
    "password123",
    "123456789",
    "1234567890",
    "qwertyuiop",
    "letmein123",
    "welcome123",
    "admin12345",
    "iloveyou123",
    "changeme123",
    "india12345",
}

_phone_re = re.compile(r"^(?:\+91|91|0)?([6-9]\d{9})$")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def validate_password_strength(password: str, *, email: str | None = None) -> None:
    """Raise ValueError with a stable code for weak passwords."""
    if len(password) < settings.password_min_length:
        raise ValueError(f"password_too_short:{settings.password_min_length}")
    if len(password) > 200:
        raise ValueError("password_too_long")
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        raise ValueError("password_too_common")
    if email:
        local = email.split("@", 1)[0].lower()
        if local and len(local) >= 4 and local in lowered:
            raise ValueError("password_contains_email")
    if len(set(password)) < 4:
        raise ValueError("password_too_simple")


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_identifier(value: str) -> str:
    """Keyed hash for IP addresses / phone numbers used in logs and rate-limit keys."""
    return hmac.new(settings.secret_key.encode(), value.strip().lower().encode(), hashlib.sha256).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def normalize_phone(raw: str) -> str | None:
    """Return canonical +91XXXXXXXXXX or None when unusable."""
    cleaned = re.sub(r"[\s()\-.]", "", raw or "")
    match = _phone_re.match(cleaned)
    if not match:
        return None
    return f"+91{match.group(1)}"


def mask_phone(phone: str | None) -> str | None:
    if not phone or len(phone) < 6:
        return None
    return f"{phone[:3]}{'*' * (len(phone) - 5)}{phone[-2:]}"


def _fernet() -> Fernet:
    key = settings.encryption_key
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        # Accept raw 32-byte base64 from older deployments without silently weakening.
        digest = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_value(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:  # pragma: no cover - key rotation guard
        raise ValueError("decryption_failed") from exc


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, *, account_name: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name="HVA Assist")


def verify_totp(secret: str, code: str) -> bool:
    if not code or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str, *, purpose: str) -> str:
    return hmac.new(
        settings.secret_key.encode(), f"{purpose}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def utcnow() -> datetime:
    return datetime.now(UTC)
