import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import ValidationError

from app.core.security.authentication import get_active_user_id
from app.moderation.rate_limits import moderator_limited_user
from app.payments.schemas import PlaceholderWebhookEvent, RefundDecision, RefundRequestCreate
from app.payments.service import (
    decide_refund,
    list_refunds,
    process_webhook,
    request_refund,
    verify_webhook_signature,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/webhooks/placeholder")
async def placeholder_webhook(
    request: Request,
    x_payment_event_id: str = Header(min_length=1, max_length=200),
    x_payment_timestamp: str = Header(min_length=1, max_length=20),
    x_payment_signature: str = Header(min_length=1, max_length=200),
) -> dict[str, object]:
    raw_body = await request.body()
    verify_webhook_signature(raw_body, x_payment_event_id, x_payment_timestamp, x_payment_signature)
    try:
        event = PlaceholderWebhookEvent.model_validate(json.loads(raw_body))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="Invalid payment event payload.") from exc
    return process_webhook(x_payment_event_id, event)


@router.post("/{payment_id}/refund-requests", status_code=201)
def post_refund_request(
    payment_id: str,
    payload: RefundRequestCreate,
    user_id: str = Depends(get_active_user_id),
) -> dict[str, object]:
    return request_refund(payment_id, user_id, payload.reason)


@router.get("/refund-requests")
def get_refund_requests(
    status: str | None = None,
    _: str = Depends(moderator_limited_user),
) -> list[dict[str, object]]:
    if status not in {None, "requested", "approved", "rejected", "completed"}:
        raise HTTPException(status_code=422, detail="Invalid refund status.")
    return list_refunds(status)


@router.patch("/refund-requests/{refund_id}")
def patch_refund_request(
    refund_id: str,
    payload: RefundDecision,
    _: str = Depends(moderator_limited_user),
) -> dict[str, object]:
    return decide_refund(refund_id, payload.decision, payload.note)
