"""Small process-local limiter for the public chatbot endpoint.

Cloud Run is currently configured for one instance. This is intentionally a
defence-in-depth guard, not a substitute for an edge/shared limiter.
"""
from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status

_WINDOW_SECONDS = 60.0
_MAX_REQUESTS = 10
_requests: dict[str, deque[float]] = defaultdict(deque)


def enforce_chat_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    now = monotonic()
    bucket = _requests[client]
    while bucket and now - bucket[0] >= _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Chat rate limit exceeded. Please try again shortly.",
        )
    bucket.append(now)
