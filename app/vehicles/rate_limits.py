from app.core.security.rate_limiting import (
    RatePolicy,
    authenticated_rate_limit,
    enforce_rate_limit,
)

READ = RatePolicy("vehicles:read", 120, 60)
CREATE = RatePolicy("vehicles:create", 10, 60 * 60)
PAYMENT_STATUS = RatePolicy("vehicles:payment-status", 30, 60)
PUBLISH = RatePolicy("vehicles:publish", 10, 60)
IMAGE_UPLOAD = RatePolicy("vehicles:image-upload", 60, 60 * 60)
IMAGE_ORDER = RatePolicy("vehicles:image-order", 30, 60)
EDIT = RatePolicy("vehicles:edit", 30, 60 * 60)
STATUS = RatePolicy("vehicles:status", 30, 60 * 60)
DELETE = RatePolicy("vehicles:delete", 10, 60 * 60)


read_limited_user = authenticated_rate_limit(READ)
create_limited_user = authenticated_rate_limit(CREATE)
payment_limited_user = authenticated_rate_limit(PAYMENT_STATUS)
publish_limited_user = authenticated_rate_limit(PUBLISH)
image_order_limited_user = authenticated_rate_limit(IMAGE_ORDER)
edit_limited_user = authenticated_rate_limit(EDIT)
status_limited_user = authenticated_rate_limit(STATUS)
delete_limited_user = authenticated_rate_limit(DELETE)


def check_image_upload_limit(user_id: str, image_count: int) -> None:
    enforce_rate_limit(user_id, IMAGE_UPLOAD, cost=image_count)
