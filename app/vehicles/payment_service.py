from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.config import settings
from app.db.supabase import get_supabase
from app.vehicles.access import check_vehicle_type, get_owned_listing


def create_pending_payment(vehicle_type: str, listing_id: str, user_id: str) -> None:
    get_supabase().table("listing_payments").insert({
        "user_id": user_id,
        "vehicle_type": vehicle_type,
        "listing_id": listing_id,
        "provider": "placeholder",
        "status": "pending",
        "amount": settings.listing_fee_chf,
        "currency": "CHF",
    }).execute()


def _placeholder_payment_successful() -> bool:
    if settings.is_production:
        return False
    return settings.payment_placeholder_enabled


def get_payment_status(vehicle_type: str, vehicle_id: str, user_id: str) -> dict[str, object]:
    listing = get_owned_listing(vehicle_type, vehicle_id, user_id)
    successful = listing.get("payment_status") == "paid"
    if not successful and _placeholder_payment_successful():
        _mark_placeholder_paid(vehicle_type, vehicle_id, user_id)
        successful = True

    return {
        "successful": successful,
        "payment_status": "paid" if successful else listing.get("payment_status", "pending"),
        "provider": "not_configured" if settings.is_production else "placeholder",
    }


def ensure_payment_completed(vehicle_type: str, vehicle_id: str, user_id: str) -> None:
    check_vehicle_type(vehicle_type)
    listing = get_owned_listing(vehicle_type, vehicle_id, user_id)
    if listing.get("payment_status") == "paid":
        return
    if settings.is_production:
        raise HTTPException(status_code=503, detail="Der produktive Zahlungsanbieter ist noch nicht konfiguriert.")
    if _placeholder_payment_successful():
        _mark_placeholder_paid(vehicle_type, vehicle_id, user_id)
        return
    raise HTTPException(status_code=402, detail="Payment has not been completed.")


def _mark_placeholder_paid(vehicle_type: str, vehicle_id: str, user_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    get_supabase().table("listing_payments").update({
        "status": "paid",
        "paid_at": now,
    }).eq("vehicle_type", vehicle_type).eq("listing_id", vehicle_id).eq("user_id", user_id).execute()
    get_supabase().table(vehicle_type).update({
        "payment_status": "paid",
        "paid_at": now,
    }).eq("id", vehicle_id).eq("profile_id", user_id).execute()
