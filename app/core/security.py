"""Request-protection primitives and admin authentication helpers.

CSRF (itsdangerous) and in-memory rate limiter are unchanged from Stage 1.
JWT creation/verification and Argon2 password hashing are added for the
SQLAdmin authenticated panel.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pwdlib import PasswordHash

# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------
_CSRF_SALT = "pm-csrf"
_DEFAULT_MAX_AGE = 60 * 60 * 4  # 4 hours


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt=_CSRF_SALT)


def issue_csrf_token(secret_key: str) -> str:
    return _serializer(secret_key).dumps("csrf")


def validate_csrf_token(
    secret_key: str, token: str | None, max_age: int = _DEFAULT_MAX_AGE
) -> bool:
    if not token:
        return False
    try:
        _serializer(secret_key).loads(token, max_age=max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """Thread-safe in-memory fixed-window rate limiter."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            hits = [t for t in self._hits[key] if t > cutoff]
            if len(hits) >= self.limit:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


# ---------------------------------------------------------------------------
# Password hashing (admin)
# ---------------------------------------------------------------------------
_pwd_context = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT (admin session tokens)
# ---------------------------------------------------------------------------
def create_access_token(
    data: Dict[str, Any],
    secret: str,
    algorithm: str = "HS256",
    expires_minutes: int = 60,
) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, secret, algorithm=algorithm)


def verify_token(token: str, secret: str, algorithm: str = "HS256") -> Dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise ValueError("Admin token has expired.")
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Invalid admin token: {exc}")
