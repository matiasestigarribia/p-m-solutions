"""CSRF token signing and a local (no external service) rate limiter."""
import time

from app.core.security import (
    RateLimiter,
    issue_csrf_token,
    validate_csrf_token,
)

SECRET = "test-secret"


def test_csrf_token_roundtrips():
    token = issue_csrf_token(SECRET)
    assert isinstance(token, str) and token
    assert validate_csrf_token(SECRET, token) is True


def test_csrf_rejects_tampered_token():
    token = issue_csrf_token(SECRET)
    assert validate_csrf_token(SECRET, token + "x") is False


def test_csrf_rejects_wrong_secret():
    token = issue_csrf_token(SECRET)
    assert validate_csrf_token("other-secret", token) is False


def test_csrf_rejects_missing_token():
    assert validate_csrf_token(SECRET, None) is False
    assert validate_csrf_token(SECRET, "") is False


def test_csrf_expires():
    token = issue_csrf_token(SECRET)
    assert validate_csrf_token(SECRET, token, max_age=-1) is False


def test_rate_limiter_allows_then_blocks():
    rl = RateLimiter(limit=3, window_seconds=100)
    assert rl.allow("1.2.3.4") is True
    assert rl.allow("1.2.3.4") is True
    assert rl.allow("1.2.3.4") is True
    assert rl.allow("1.2.3.4") is False  # 4th within window


def test_rate_limiter_is_per_key():
    rl = RateLimiter(limit=1, window_seconds=100)
    assert rl.allow("a") is True
    assert rl.allow("b") is True
    assert rl.allow("a") is False


def test_rate_limiter_window_resets():
    rl = RateLimiter(limit=1, window_seconds=0.05)
    assert rl.allow("k") is True
    assert rl.allow("k") is False
    time.sleep(0.06)
    assert rl.allow("k") is True
