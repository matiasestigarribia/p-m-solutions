"""Local request-protection primitives for Stage 1.

No external service is used. CSRF tokens are signed with ``itsdangerous`` using
the app ``secret_key``; the rate limiter is an in-process fixed-window counter.
Both are adequate for a single-instance Stage 1 deployment. NOTE: the in-memory
limiter does not share state across Cloud Run instances — Stage 2 can swap it
for a shared backend behind the same ``RateLimiter`` surface.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_CSRF_SALT = "pm-csrf"
_DEFAULT_MAX_AGE = 60 * 60 * 4  # 4 hours


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt=_CSRF_SALT)


def issue_csrf_token(secret_key: str) -> str:
    return _serializer(secret_key).dumps("csrf")


def validate_csrf_token(secret_key: str, token: str | None,
                        max_age: int = _DEFAULT_MAX_AGE) -> bool:
    if not token:
        return False
    try:
        _serializer(secret_key).loads(token, max_age=max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False


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
