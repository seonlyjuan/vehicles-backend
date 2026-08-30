from fastapi import HTTPException

from app.db.supabase import get_supabase
from app.locations.service import validate_swiss_location
from app.vehicles.access import check_vehicle_type
from app.vehicles.constants import VALID_TYPES
from app.vehicles.filters import VEHICLE_FILTERS, validate_filters
from app.vehicles.fields import public_listing_data, public_listing_fields
from app.vehicles.image_queries import add_listing_images
from app.vehicles.payment_service import create_pending_payment

PRIVATE_ACTIVE_LIMIT = 10
DEALER_ACTIVE_LIMIT = 100


def _validate_vehicle_payload(vehicle_type: str, payload: dict[str, object]) -> None:
    if vehicle_type in {"cars", "motorbikes"} and not payload.get("model"):
        raise HTTPException(status_code=422, detail="Für Autos und Motorräder ist das Modell erforderlich.")
    if vehicle_type == "bicycles":
        payload.pop("power", None)
        payload.pop("mileage", None)
        payload.pop("first_registration", None)
    if payload.get("condition") == "damaged" and not str(payload.get("known_defects") or "").strip():
        raise HTTPException(status_code=422, detail="Bei beschädigten Fahrzeugen müssen bekannte Mängel angegeben werden.")


def _enforce_active_listing_limit(user_id: str) -> None:
    supabase = get_supabase()
    profile_response = (
        supabase.table("profiles").select("seller_type")
        .eq("id", user_id).limit(1).execute()
    )
    seller_type = profile_response.data[0].get("seller_type") if profile_response.data else "private"
    limit = DEALER_ACTIVE_LIMIT if seller_type == "dealer" else PRIVATE_ACTIVE_LIMIT
    count = 0
    for vehicle_type in VALID_TYPES:
        response = (
            supabase.table(vehicle_type).select("id", count="exact")
            .eq("profile_id", user_id).in_("status", ["draft", "active", "archived"]).execute()
        )
        count += response.count or 0
    if count >= limit:
        raise HTTPException(status_code=409, detail=f"Du kannst höchstens {limit} laufende Inserate verwalten.")


def create_listing(vehicle_type: str, user_id: str, payload: dict[str, object]) -> dict[str, object]:
    check_vehicle_type(vehicle_type)
    _validate_vehicle_payload(vehicle_type, payload)
    location = validate_swiss_location(
        str(payload["postal_code"]), str(payload["locality"]), str(payload["canton"])
    )
    payload.update(location)
    _enforce_active_listing_limit(user_id)

    response = get_supabase().table(vehicle_type).insert({
        **payload,
        "profile_id": user_id,
        "status": "draft",
        "payment_status": "pending",
    }).execute()
    listing = response.data[0]
    try:
        create_pending_payment(vehicle_type, listing["id"], user_id)
    except Exception:
        get_supabase().table(vehicle_type).delete().eq("id", listing["id"]).eq("profile_id", user_id).execute()
        raise
    return listing


def list_listings(
    vehicle_type: str,
    page: int,
    per_page: int,
    filters: dict[str, object] | None = None,
) -> dict[str, object]:
    check_vehicle_type(vehicle_type)
    filters = filters or {}
    validate_filters(vehicle_type, filters)
    start = (page - 1) * per_page
    query = get_supabase().table(vehicle_type).select(
        public_listing_fields(vehicle_type), count="exact"
    ).eq("status", "active")
    if filters.get("brand"):
        query = query.ilike("brand", f"%{str(filters['brand']).strip()}%")
    if filters.get("model"):
        query = query.ilike("model", f"%{str(filters['model']).strip()}%")
    if filters.get("canton"):
        query = query.eq("canton", filters["canton"])
    if filters.get("postal_code"):
        query = query.eq("postal_code", filters["postal_code"])
    for name in ("price", "year", "power"):
        if name not in VEHICLE_FILTERS[vehicle_type]:
            continue
        if filters.get(f"{name}_min") is not None:
            query = query.gte(name, filters[f"{name}_min"])
        if filters.get(f"{name}_max") is not None:
            query = query.lte(name, filters[f"{name}_max"])
    response = query.order("created_at", desc=True).range(start, start + per_page - 1).execute()
    items = response.data or []
    for item in items:
        item["vehicle_type"] = vehicle_type
    add_listing_images(items)
    _add_public_sellers(items)
    total = response.count or 0
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


def get_listing(vehicle_type: str, vehicle_id: str, user_id: str) -> dict[str, object]:
    check_vehicle_type(vehicle_type)
    response = get_supabase().table(vehicle_type).select("*").eq("id", vehicle_id).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Listing not found.")
    item = response.data[0]
    if item.get("status") != "active" and item.get("profile_id") != user_id:
        raise HTTPException(status_code=404, detail="Listing not found.")
    if item.get("profile_id") != user_id:
        item = public_listing_data(item)
    item["vehicle_type"] = vehicle_type
    add_listing_images([item])
    _add_public_sellers([item])
    return item


def list_profile_listings(user_id: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for vehicle_type in sorted(VALID_TYPES):
        response = (
            get_supabase().table(vehicle_type).select("*")
            .eq("profile_id", user_id).neq("status", "deleted").execute()
        )
        for item in response.data or []:
            item["vehicle_type"] = vehicle_type
            items.append(item)
    add_listing_images(items)
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def _add_public_sellers(items: list[dict[str, object]]) -> None:
    profile_ids = list({item["profile_id"] for item in items if item.get("profile_id")})
    if not profile_ids:
        return
    response = (
        get_supabase().table("profiles")
        .select("id, username, seller_type, company_name, dealer_verification_status")
        .in_("id", profile_ids).execute()
    )
    profiles = {profile["id"]: profile for profile in response.data or []}
    for item in items:
        profile = profiles.get(item.get("profile_id"), {})
        item["seller"] = {
            "username": profile.get("username"),
            "seller_type": profile.get("seller_type", "private"),
            "company_name": profile.get("company_name"),
            "is_verified_dealer": profile.get("dealer_verification_status") == "verified",
        }
