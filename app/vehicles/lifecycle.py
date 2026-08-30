from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.core.config import settings
from app.db.supabase import get_supabase
from app.locations.service import validate_swiss_location
from app.vehicles.access import get_owned_listing
from app.vehicles.image_service import delete_listing_images
from app.vehicles.payment_service import ensure_payment_completed

STATUS_TRANSITIONS = {
    "archive": ({"active", "sold"}, "archived"),
    "reactivate": ({"archived"}, "active"),
    "mark_sold": ({"active"}, "sold"),
}


def update_listing(
    vehicle_type: str,
    vehicle_id: str,
    user_id: str,
    changes: dict[str, object],
) -> dict[str, object]:
    listing = get_owned_listing(vehicle_type, vehicle_id, user_id)
    if listing.get("status") in {"deleted", "suspended"}:
        raise HTTPException(status_code=409, detail="Dieses Inserat kann derzeit nicht bearbeitet werden.")
    if vehicle_type == "bicycles":
        for field in ("power", "mileage", "first_registration"):
            changes.pop(field, None)
    next_condition = changes.get("condition", listing.get("condition"))
    next_defects = changes.get("known_defects", listing.get("known_defects"))
    if next_condition == "damaged" and not str(next_defects or "").strip():
        raise HTTPException(status_code=422, detail="Bei beschädigten Fahrzeugen müssen bekannte Mängel angegeben werden.")

    location_fields = {"postal_code", "locality", "canton"}
    if location_fields.intersection(changes):
        location = validate_swiss_location(
            str(changes.get("postal_code", listing.get("postal_code", ""))),
            str(changes.get("locality", listing.get("locality", ""))),
            str(changes.get("canton", listing.get("canton", ""))),
        )
        changes.update(location)
    changes["updated_at"] = _now()
    response = (
        get_supabase().table(vehicle_type).update(changes)
        .eq("id", vehicle_id).eq("profile_id", user_id).execute()
    )
    return response.data[0]


def change_listing_status(
    vehicle_type: str,
    vehicle_id: str,
    user_id: str,
    action: str,
) -> dict[str, object]:
    listing = get_owned_listing(vehicle_type, vehicle_id, user_id)
    next_status = resolve_listing_status(str(listing.get("status")), action)
    if action == "reactivate":
        ensure_payment_completed(vehicle_type, vehicle_id, user_id)
        expires_at = listing.get("expires_at")
        if expires_at and datetime.fromisoformat(str(expires_at).replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=409, detail="Das Inserat ist abgelaufen und muss verlängert werden.")

    timestamp_field = {
        "archive": "archived_at",
        "reactivate": "archived_at",
        "mark_sold": "sold_at",
    }[action]
    values: dict[str, object] = {"status": next_status, "updated_at": _now()}
    values[timestamp_field] = None if action == "reactivate" else _now()
    response = (
        get_supabase().table(vehicle_type).update(values)
        .eq("id", vehicle_id).eq("profile_id", user_id).execute()
    )
    return response.data[0]


def publish_listing(vehicle_type: str, vehicle_id: str, user_id: str) -> dict[str, object]:
    listing = get_owned_listing(vehicle_type, vehicle_id, user_id)
    if listing.get("status") == "active":
        return listing
    if listing.get("status") != "draft":
        raise HTTPException(status_code=409, detail="Only draft listings can be published.")
    _ensure_seller_can_publish(user_id)
    ensure_payment_completed(vehicle_type, vehicle_id, user_id)
    now = datetime.now(timezone.utc)
    response = (
        get_supabase().table(vehicle_type).update({
            "status": "active",
            "payment_status": "paid",
            "paid_at": listing.get("paid_at") or now.isoformat(),
            "expires_at": (now + timedelta(days=settings.listing_duration_days)).isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", vehicle_id).eq("profile_id", user_id).execute()
    )
    if not response.data:
        raise HTTPException(status_code=409, detail="Listing could not be published.")
    return response.data[0]


def delete_listing(vehicle_type: str, vehicle_id: str, user_id: str) -> None:
    listing = get_owned_listing(vehicle_type, vehicle_id, user_id)
    now = _now()
    if listing.get("status") != "deleted":
        get_supabase().table(vehicle_type).update({
            "status": "deleted",
            "deleted_at": now,
            "updated_at": now,
        }).eq("id", vehicle_id).eq("profile_id", user_id).execute()
        get_supabase().table("conversations").update({
            "status": "closed",
            "updated_at": now,
        }).eq("vehicle_type", vehicle_type).eq("listing_id", vehicle_id).execute()
    delete_listing_images(vehicle_type, vehicle_id, user_id)


def _ensure_seller_can_publish(user_id: str) -> None:
    response = (
        get_supabase().table("profiles")
        .select("seller_type, dealer_verification_status")
        .eq("id", user_id).limit(1).execute()
    )
    if not response.data:
        return
    profile = response.data[0]
    if profile.get("seller_type") == "dealer" and profile.get("dealer_verification_status") != "verified":
        raise HTTPException(status_code=403, detail="Händler müssen vor der Veröffentlichung verifiziert werden.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_listing_status(current_status: str, action: str) -> str:
    transition = STATUS_TRANSITIONS.get(action)
    if not transition or current_status not in transition[0]:
        raise HTTPException(status_code=409, detail="Dieser Statuswechsel ist nicht erlaubt.")
    return transition[1]
