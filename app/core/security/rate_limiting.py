import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException

from app.core.security.authentication import get_active_user_id
from app.core.config import settings


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


class RedisRateLimiter:
    """Shared fixed-window limiter for production with multiple API instances."""

    _SCRIPT = """
    local used = redis.call('INCRBY', KEYS[1], ARGV[1])
    if used == tonumber(ARGV[1]) then
      redis.call('EXPIRE', KEYS[1], ARGV[2])
    end
    return {used, redis.call('TTL', KEYS[1])}
    """

    def __init__(self, url: str) -> None:
        from redis import Redis

        self._client = Redis.from_url(url, decode_responses=True)

    def check(self, subject: str, policy: RatePolicy, cost: int = 1) -> None:
        key = f"rate-limit:{policy.scope}:{subject}"
        try:
            used, ttl = self._client.eval(self._SCRIPT, 1, key, cost, policy.window_seconds)
            used = int(used)
            retry_after = max(1, int(ttl))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Rate-limit service unavailable.") from exc
        if used > policy.limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )


rate_limiter = RedisRateLimiter(settings.redis_url) if settings.redis_url else InMemoryRateLimiter()


def enforce_rate_limit(subject: str, policy: RatePolicy, cost: int = 1) -> None:
    rate_limiter.check(subject, policy, cost)


def authenticated_rate_limit(policy: RatePolicy) -> Callable[..., str]:
    def limited_user(user_id: str = Depends(get_active_user_id)) -> str:
        enforce_rate_limit(user_id, policy)
        return user_id

    return limited_user
