import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException


@dataclass(frozen=True)
class RatePolicy:
    scope: str
    limit: int
    window_seconds: int


@dataclass
class _Window:
    used: int
    resets_at: float


class InMemoryRateLimiter:
    """Thread-safe fixed-window limiter. Replace this store with Redis for multi-instance deployments."""

    def __init__(self) -> None:
        self._windows: dict[tuple[str, str], _Window] = {}
        self._lock = threading.Lock()

    def check(self, subject: str, policy: RatePolicy, cost: int = 1) -> None:
        now = time.monotonic()
        key = (policy.scope, subject)
        with self._lock:
            window = self._windows.get(key)
            if window is None or window.resets_at <= now:
                window = _Window(used=0, resets_at=now + policy.window_seconds)
                self._windows[key] = window

            retry_after = max(1, int(window.resets_at - now) + 1)
            if window.used + cost > policy.limit:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            window.used += cost


rate_limiter = InMemoryRateLimiter()
