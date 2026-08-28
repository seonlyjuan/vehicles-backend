from fastapi import Depends

from app.core.auth import get_current_user_id
from app.core.rate_limit import RatePolicy, rate_limiter

READ = RatePolicy("vehicles:read", 120, 60)
CREATE = RatePolicy("vehicles:create", 10, 60 * 60)
PAYMENT_STATUS = RatePolicy("vehicles:payment-status", 30, 60)
PUBLISH = RatePolicy("vehicles:publish", 10, 60)
IMAGE_UPLOAD = RatePolicy("vehicles:image-upload", 60, 60 * 60)
IMAGE_ORDER = RatePolicy("vehicles:image-order", 30, 60)


def _limited_user(user_id: str, policy: RatePolicy) -> str:
    rate_limiter.check(user_id, policy)
    return user_id


def read_limited_user(user_id: str = Depends(get_current_user_id)) -> str:
    return _limited_user(user_id, READ)


def create_limited_user(user_id: str = Depends(get_current_user_id)) -> str:
    return _limited_user(user_id, CREATE)


def payment_limited_user(user_id: str = Depends(get_current_user_id)) -> str:
    return _limited_user(user_id, PAYMENT_STATUS)


def publish_limited_user(user_id: str = Depends(get_current_user_id)) -> str:
    return _limited_user(user_id, PUBLISH)


def image_order_limited_user(user_id: str = Depends(get_current_user_id)) -> str:
    return _limited_user(user_id, IMAGE_ORDER)


def check_image_upload_limit(user_id: str, image_count: int) -> None:
    rate_limiter.check(user_id, IMAGE_UPLOAD, cost=image_count)
