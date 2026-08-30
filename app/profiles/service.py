from fastapi import HTTPException

from app.db.supabase import get_supabase
from app.locations.service import validate_swiss_location
from app.profiles.schemas import SellerProfileUpdate

PROFILE_FIELDS = (
    "username, seller_type, platform_role, account_status, company_name, "
    "business_address, business_postal_code, business_locality, business_canton, "
    "uid_number, commercial_register_number, business_email, business_phone, "
    "dealer_verification_status, dealer_verified_at"
)
DEALER_IDENTITY_FIELDS = (
    "company_name", "business_address", "business_postal_code", "business_locality",
    "business_canton", "uid_number", "commercial_register_number", "business_email",
    "business_phone",
)


def get_profile(user_id: str) -> dict[str, object]:
    response = (
        get_supabase().table("profiles").select(PROFILE_FIELDS)
        .eq("id", user_id).limit(1).execute()
    )
    if response.data:
        return response.data[0]
    return {
        "username": None,
        "seller_type": "private",
        "platform_role": "user",
        "account_status": "active",
        "dealer_verification_status": "not_requested",
    }


def update_username(user_id: str, username: str) -> dict[str, str]:
    try:
        response = get_supabase().table("profiles").upsert(
            {"id": user_id, "username": username.lower()}, on_conflict="id"
        ).execute()
    except Exception as exc:
        if "23505" in str(exc):
            raise HTTPException(status_code=409, detail="Dieser Username ist bereits vergeben.") from exc
        raise
    return {"username": response.data[0]["username"]}


def update_seller_profile(user_id: str, payload: SellerProfileUpdate) -> dict[str, object]:
    current_response = (
        get_supabase().table("profiles").select(
            "seller_type, dealer_verification_status, dealer_verified_at, "
            + ", ".join(DEALER_IDENTITY_FIELDS)
        )
        .eq("id", user_id).limit(1).execute()
    )
    current = current_response.data[0] if current_response.data else {}
    if (
        current.get("seller_type") == "dealer"
        and current.get("dealer_verification_status") == "verified"
        and payload.seller_type == "private"
    ):
        raise HTTPException(
            status_code=409,
            detail="Ein verifiziertes Händlerkonto kann nur durch den Support auf privat umgestellt werden.",
        )
    values = payload.model_dump(mode="json")
    if payload.seller_type == "dealer":
        validate_swiss_location(
            payload.business_postal_code or "",
            payload.business_locality or "",
            payload.business_canton or "",
        )
        dealer_data_changed = any(current.get(field) != values.get(field) for field in DEALER_IDENTITY_FIELDS)
        if current.get("dealer_verification_status") == "verified" and not dealer_data_changed:
            values["dealer_verification_status"] = "verified"
            values["dealer_verified_at"] = current.get("dealer_verified_at")
        else:
            values["dealer_verification_status"] = "pending"
            values["dealer_verified_at"] = None
    else:
        for field in DEALER_IDENTITY_FIELDS:
            values[field] = None
        values["dealer_verification_status"] = "not_requested"
        values["dealer_verified_at"] = None

    response = get_supabase().table("profiles").upsert(
        {"id": user_id, **values}, on_conflict="id"
    ).execute()
    return response.data[0]
