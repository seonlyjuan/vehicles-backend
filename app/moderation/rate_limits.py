from fastapi import Depends

from app.core.security.authorization import require_moderator
from app.core.security.rate_limiting import RatePolicy, enforce_rate_limit

MODERATION = RatePolicy("moderation:actions", 120, 60 * 60)


def moderator_limited_user(user_id: str = Depends(require_moderator)) -> str:
    enforce_rate_limit(user_id, MODERATION)
    return user_id

