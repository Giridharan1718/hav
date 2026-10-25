"""Rate limiting.

The in-memory sliding-window limiter is correct for a single API process (local
development and a single-instance deployment). Running multiple instances requires a
shared counter store; that constraint is documented rather than hidden.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request

from app.core.errors import ApiError
from app.core.security import hash_identifier


@dataclass(frozen=True)
class Limit:
    times: int
    seconds: int


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: Limit) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - limit.seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit.times:
                retry_after = max(1, int(bucket[0] + limit.seconds - now) + 1)
                return False, retry_after
            bucket.append(now)
            if len(self._hits) > 50_000:  # bound memory under abuse
                self._prune(cutoff)
            return True, 0

    def _prune(self, cutoff: float) -> None:
        stale = [key for key, bucket in self._hits.items() if not bucket or bucket[-1] < cutoff]
        for key in stale[:10_000]:
            self._hits.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def enforce(limit: Limit, *, scope: str, request: Request, identity: str | None = None) -> None:
    client = request.client.host if request.client else "unknown"
    subject = identity or hash_identifier(client)
    allowed, retry_after = limiter.check(f"{scope}:{subject}", limit)
    if not allowed:
        raise ApiError(
            429,
            "rate_limited",
            "Too many requests. Please wait and try again.",
            headers={"Retry-After": str(retry_after)},
        )


# Documented per-endpoint policies (also listed in docs/api.md).
LIMITS = {
    "register": Limit(5, 3600),
    "login": Limit(10, 900),
    "mfa": Limit(10, 900),
    "password_reset_request": Limit(5, 3600),
    "password_reset_confirm": Limit(10, 3600),
    "phone_challenge": Limit(5, 3600),
    "phone_verify": Limit(10, 3600),
    "search": Limit(120, 60),
    "assistant": Limit(30, 3600),
    "postal": Limit(60, 60),
    "draft_export": Limit(10, 3600),
    "data_export": Limit(3, 3600),
    "admin_write": Limit(60, 3600),
}
