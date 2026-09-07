import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.core.config import settings
from app.db.supabase import get_supabase
from app.payments.schemas import PlaceholderWebhookEvent


def verify_webhook_signature(raw_body: bytes, event_id: str, timestamp: str, signature: str) -> None:
    """Verify the documented placeholder HMAC scheme and reject replayed requests."""
    if not settings.payment_webhook_secret:
        raise HTTPException(status_code=503, detail="Payment webhook secret is not configured.")
    try:
        timestamp_value = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid webhook timestamp.") from exc
    if abs(int(time.time()) - timestamp_value) > settings.payment_webhook_tolerance_seconds:
        raise HTTPException(status_code=401, detail="Expired webhook timestamp.")
    signed_payload = timestamp.encode("ascii") + b"." + event_id.encode("utf-8") + b"." + raw_body
    expected = hmac.new(
        settings.payment_webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    supplied = signature.removeprefix("sha256=")
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")


def process_webhook(event_id: str, event: PlaceholderWebhookEvent) -> dict[str, object]:
    """Atomically deduplicate and apply a provider event inside PostgreSQL."""
    try:
        response = get_supabase().rpc("process_placeholder_payment_webhook", {
            "p_event_id": event_id,
            "p_transaction_id": event.transaction_id,
            "p_vehicle_type": event.vehicle_type,
            "p_listing_id": event.listing_id,
            "p_status": event.status,
            "p_amount": str(event.amount),
            "p_currency": event.currency,
            "p_payload": event.model_dump(mode="json"),
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Payment event could not be applied.") from exc
    return response.data or {"processed": True}


def request_refund(payment_id: str, user_id: str, reason: str) -> dict[str, object]:
    supabase = get_supabase()
    response = (
        supabase.table("listing_payments").select("id, status, paid_at")
        .eq("id", payment_id).eq("user_id", user_id).limit(1).execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Payment not found.")
    payment = response.data[0]
    if payment.get("status") != "paid" or not payment.get("paid_at"):
        raise HTTPException(status_code=409, detail="Only a completed payment can be refunded.")
    paid_at = datetime.fromisoformat(str(payment["paid_at"]).replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > paid_at + timedelta(days=settings.refund_window_days):
        raise HTTPException(status_code=409, detail="The configured refund request window has expired.")
    try:
        created = supabase.table("payment_refund_requests").insert({
            "payment_id": payment_id,
            "user_id": user_id,
            "reason": reason.strip(),
            "status": "requested",
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=409, detail="A refund request already exists.") from exc
    return created.data[0]


def decide_refund(refund_id: str, decision: str, note: str) -> dict[str, object]:
    """Record a review decision; approval still awaits a provider refund callback."""
    supabase = get_supabase()
    response = (
        supabase.table("payment_refund_requests").select("id, status")
        .eq("id", refund_id).limit(1).execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Refund request not found.")
    if response.data[0].get("status") != "requested":
        raise HTTPException(status_code=409, detail="Refund request has already been reviewed.")
    updated = (
        supabase.table("payment_refund_requests").update({
            "status": "approved" if decision == "approve" else "rejected",
            "decision_note": note.strip(),
            "decided_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", refund_id).eq("status", "requested").execute()
    )
    if not updated.data:
        raise HTTPException(status_code=409, detail="Refund request has already been reviewed.")
    return updated.data[0]


def list_refunds(status: str | None) -> list[dict[str, object]]:
    query = (
        get_supabase().table("payment_refund_requests")
        .select("*, listing_payments(vehicle_type, listing_id, amount, currency)")
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    return query.execute().data or []
