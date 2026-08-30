from fastapi import APIRouter, Depends, Response

from app.core.security.rate_limiting import RatePolicy, authenticated_rate_limit
from app.notifications.service import list_notifications, mark_notifications_read

router = APIRouter(prefix="/notifications", tags=["notifications"])
read_limited_user = authenticated_rate_limit(RatePolicy("notifications:read", 60, 60))
update_limited_user = authenticated_rate_limit(RatePolicy("notifications:update", 60, 60))


@router.get("")
def get_notifications(user_id: str = Depends(read_limited_user)) -> dict[str, object]:
    return list_notifications(user_id)


@router.post("/read", status_code=204)
def post_notifications_read(user_id: str = Depends(update_limited_user)) -> Response:
    mark_notifications_read(user_id)
    return Response(status_code=204)


@router.post("/{notification_id}/read", status_code=204)
def post_notification_read(
    notification_id: str,
    user_id: str = Depends(update_limited_user),
) -> Response:
    mark_notifications_read(user_id, notification_id)
    return Response(status_code=204)

