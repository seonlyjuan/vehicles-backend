from fastapi import HTTPException

from app.db.supabase import get_supabase

VALID_TYPES = {"bicycles", "cars", "motorbikes"}


def check_vehicle_type(vehicle_type: str) -> None:
    if vehicle_type not in VALID_TYPES:
        raise HTTPException(status_code=404, detail="Unknown vehicle type.")


def get_owned_listing(vehicle_type: str, vehicle_id: str, user_id: str) -> dict[str, object]:
    check_vehicle_type(vehicle_type)
    response = (
        get_supabase().table(vehicle_type)
        .select("*")
        .eq("id", vehicle_id)
        .eq("profile_id", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Listing not found.")
    return response.data[0]
