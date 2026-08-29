from fastapi import Depends

from app.core.auth import get_current_user_id
from app.core.rate_limit import RatePolicy, rate_limiter

READ = RatePolicy("messages:read", 120, 60)
START = RatePolicy("messages:start", 10, 60 * 60)
SEND = RatePolicy("messages:send", 30, 60)


def _limited_user(user_id: str, policy: RatePolicy) -> str:
    rate_limiter.check(user_id, policy)
    return user_id


def read_limited_user(user_id: str = Depends(get_current_user_id)) -> str:
    return _limited_user(user_id, READ)


def start_limited_user(user_id: str = Depends(get_current_user_id)) -> str:
    return _limited_user(user_id, START)


def send_limited_user(user_id: str = Depends(get_current_user_id)) -> str:
    return _limited_user(user_id, SEND)
