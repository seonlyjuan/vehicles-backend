from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import settings
from app.db.supabase import get_supabase
from app.vehicles.access import check_vehicle_type, get_owned_listing


def create_pending_payment(vehicle_type: str, listing_id: str, user_id: str) -> None:
    price = calculate_listing_price()
    get_supabase().table("listing_payments").insert({
        "user_id": user_id,
        "vehicle_type": vehicle_type,
        "listing_id": listing_id,
        "provider": "placeholder",
        "status": "pending",
        "amount": str(price["gross_amount"]),
        "net_amount": str(price["net_amount"]),
        "vat_amount": str(price["vat_amount"]),
        "vat_rate_percent": str(price["vat_rate_percent"]),
        "currency": "CHF",
        "metadata": {"price_includes_vat": settings.listing_fee_includes_vat},
    }).execute()


def calculate_listing_price() -> dict[str, Decimal]:
    """Return a currency-safe CHF price breakdown for the configured listing fee."""
    cents = Decimal("0.01")
    configured = settings.listing_fee_chf.quantize(cents, rounding=ROUND_HALF_UP)
    rate = settings.vat_rate_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if configured < 0 or rate < 0:
        raise RuntimeError("Listing fee and VAT rate must not be negative.")

    if rate == 0:
        net = configured
        gross = configured
    elif settings.listing_fee_includes_vat:
        gross = configured
        net = (gross / (Decimal("1") + rate / Decimal("100"))).quantize(cents, rounding=ROUND_HALF_UP)
    else:
        net = configured
        gross = (net * (Decimal("1") + rate / Decimal("100"))).quantize(cents, rounding=ROUND_HALF_UP)
    vat = gross - net
    return {
        "net_amount": net,
        "vat_amount": vat,
        "gross_amount": gross,
        "vat_rate_percent": rate,
    }


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

    payment_response = (
        get_supabase().table("listing_payments")
        .select("id, status, amount, net_amount, vat_amount, vat_rate_percent, currency, paid_at, refunded_at")
        .eq("vehicle_type", vehicle_type).eq("listing_id", vehicle_id).eq("user_id", user_id)
        .order("created_at", desc=True).limit(1).execute()
    )
    payment = payment_response.data[0] if payment_response.data else None
    refund = None
    confirmation_status = None
    if payment:
        refund_response = (
            get_supabase().table("payment_refund_requests")
            .select("id, status, reason, decision_note, created_at, decided_at, completed_at")
            .eq("payment_id", payment["id"]).eq("user_id", user_id)
            .order("created_at", desc=True).limit(1).execute()
        )
        refund = refund_response.data[0] if refund_response.data else None
        confirmation_response = (
            get_supabase().table("email_outbox").select("status")
            .eq("dedupe_key", f"payment-confirmation:{payment['id']}").limit(1).execute()
        )
        if confirmation_response.data:
            confirmation_status = confirmation_response.data[0].get("status")

    return {
        "successful": successful,
        "listing_status": listing.get("status"),
        "payment_status": payment.get("status") if payment else ("paid" if successful else listing.get("payment_status", "pending")),
        "payment_id": payment.get("id") if payment else None,
        "paid_at": payment.get("paid_at") if payment else listing.get("paid_at"),
        "refund_request": refund,
        "confirmation_email_status": confirmation_status,
        "provider": "not_configured" if settings.is_production else "placeholder",
        "price": {
            "gross_amount": str(payment["amount"]),
            "net_amount": str(payment["net_amount"]),
            "vat_amount": str(payment["vat_amount"]),
            "vat_rate_percent": str(payment["vat_rate_percent"]),
        } if payment else {key: str(value) for key, value in calculate_listing_price().items()},
        "currency": payment.get("currency", "CHF") if payment else "CHF",
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
    payment_response = (
        get_supabase().table("listing_payments").select("amount")
        .eq("vehicle_type", vehicle_type).eq("listing_id", vehicle_id).eq("user_id", user_id)
        .order("created_at", desc=True).limit(1).execute()
    )
    if not payment_response.data:
        raise HTTPException(status_code=409, detail="Payment record not found.")
    event_id = f"development-{uuid4()}"
    get_supabase().rpc("process_placeholder_payment_webhook", {
        "p_event_id": event_id,
        "p_transaction_id": f"placeholder-{vehicle_id}",
        "p_vehicle_type": vehicle_type,
        "p_listing_id": vehicle_id,
        "p_status": "paid",
        "p_amount": str(payment_response.data[0]["amount"]),
        "p_currency": "CHF",
        "p_payload": {"source": "development-placeholder", "event_id": event_id},
    }).execute()
