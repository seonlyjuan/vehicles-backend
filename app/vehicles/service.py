import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile

from app.db.supabase import get_supabase

BUCKET_NAME = "vehicles-images"
VALID_TYPES = {"bicycles", "cars", "motorbikes"}
VEHICLE_FILTERS = {
    "bicycles": ("brand", "model", "price", "year"),
    "cars": ("brand", "model", "price", "year", "power"),
    "motorbikes": ("brand", "model", "price", "year", "power"),
}
FILTER_DEFINITIONS = {
    "brand": {"name": "brand", "label": "Marke", "type": "text"},
    "model": {"name": "model", "label": "Modell", "type": "text"},
    "price": {"name": "price", "label": "Preis", "type": "range", "unit": "EUR", "min": 0},
    "year": {"name": "year", "label": "Jahr", "type": "range", "min": 1886, "max": 2100},
    "power": {"name": "power", "label": "Leistung", "type": "range", "unit": "PS", "min": 0, "max": 5000},
}
VALID_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 6


def _check_vehicle_type(vehicle_type: str) -> None:
    if vehicle_type not in VALID_TYPES:
        raise HTTPException(status_code=404, detail="Unknown vehicle type.")


def create_listing(vehicle_type: str, user_id: str, payload: dict[str, object]) -> dict[str, object]:
    _check_vehicle_type(vehicle_type)
    if vehicle_type == "bicycles":
        payload.pop("power", None)

    response = get_supabase().table(vehicle_type).insert({
        **payload,
        "profile_id": user_id,
        "status": "draft",
        "payment_status": "pending",
    }).execute()
    return response.data[0]


async def add_images(vehicle_type: str, vehicle_id: str, user_id: str, files: list[UploadFile]) -> list[dict[str, object]]:
    _check_vehicle_type(vehicle_type)
    if not files or len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Upload between 1 and {MAX_IMAGES} images.")

    supabase = get_supabase()
    uploaded_paths: list[str] = []
    images: list[dict[str, object]] = []
    try:
        for sort_order, file in enumerate(files):
            if file.content_type not in VALID_IMAGE_TYPES:
                raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed.")
            content = await file.read()
            if len(content) > MAX_IMAGE_BYTES:
                raise HTTPException(status_code=400, detail="Each image must be at most 5 MB.")

            extension = "jpg" if file.content_type == "image/jpeg" else file.content_type.split("/")[1]
            path = f"{user_id}/{vehicle_type}/{vehicle_id}/{uuid.uuid4()}.{extension}"
            supabase.storage.from_(BUCKET_NAME).upload(path, content, {"content-type": file.content_type})
            uploaded_paths.append(path)
            response = supabase.table("vehicle_images").insert({
                "profile_id": user_id,
                "vehicle_type": vehicle_type,
                "vehicle_id": vehicle_id,
                "storage_path": path,
                "content_type": file.content_type,
                "sort_order": sort_order,
            }).execute()
            images.append(response.data[0])
    except Exception:
        if uploaded_paths:
            supabase.storage.from_(BUCKET_NAME).remove(uploaded_paths)
        supabase.table("vehicle_images").delete().eq("vehicle_type", vehicle_type).eq("vehicle_id", vehicle_id).execute()
        raise
    return images


def get_filter_metadata(vehicle_type: str) -> dict[str, object]:
    _check_vehicle_type(vehicle_type)
    return {
        "vehicle_type": vehicle_type,
        "characteristics": [FILTER_DEFINITIONS[name] for name in VEHICLE_FILTERS[vehicle_type]],
    }


def _validate_filters(vehicle_type: str, filters: dict[str, object]) -> None:
    allowed = VEHICLE_FILTERS[vehicle_type]
    for name in ("price", "year", "power"):
        minimum = filters.get(f"{name}_min")
        maximum = filters.get(f"{name}_max")
        if name not in allowed and (minimum is not None or maximum is not None):
            raise HTTPException(status_code=422, detail=f"Filter '{name}' is not available for {vehicle_type}.")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise HTTPException(status_code=422, detail=f"{name}_min must not be greater than {name}_max.")


def list_listings(vehicle_type: str, page: int, per_page: int, filters: dict[str, object] | None = None) -> dict[str, object]:
    _check_vehicle_type(vehicle_type)
    filters = filters or {}
    _validate_filters(vehicle_type, filters)
    supabase = get_supabase()
    start = (page - 1) * per_page
    query = supabase.table(vehicle_type).select("*", count="exact").eq("status", "active")
    if filters.get("brand"):
        query = query.ilike("brand", f"%{filters['brand'].strip()}%")
    if filters.get("model"):
        query = query.ilike("model", f"%{filters['model'].strip()}%")
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
        image_response = supabase.table("vehicle_images").select("storage_path, sort_order").eq("vehicle_type", vehicle_type).eq("vehicle_id", item["id"]).order("sort_order").execute()
        images = []
        for image in image_response.data or []:
            signed = supabase.storage.from_(BUCKET_NAME).create_signed_url(image["storage_path"], 3600)
            images.append({"url": signed.get("signedURL") or signed.get("signedUrl"), "sort_order": image["sort_order"]})
        item["images"] = images

    total = response.count or 0
    return {"items": items, "page": page, "per_page": per_page, "total": total, "total_pages": max(1, (total + per_page - 1) // per_page)}


def get_listing(vehicle_type: str, vehicle_id: str, user_id: str) -> dict[str, object]:
    _check_vehicle_type(vehicle_type)
    supabase = get_supabase()
    response = supabase.table(vehicle_type).select("*").eq("id", vehicle_id).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Listing not found.")

    item = response.data[0]
    if item.get("status") != "active" and item.get("profile_id") != user_id:
        raise HTTPException(status_code=404, detail="Listing not found.")
    image_response = (
        supabase.table("vehicle_images")
        .select("id, storage_path, sort_order")
        .eq("vehicle_type", vehicle_type)
        .eq("vehicle_id", vehicle_id)
        .order("sort_order")
        .execute()
    )
    item["images"] = []
    for image in image_response.data or []:
        signed = supabase.storage.from_(BUCKET_NAME).create_signed_url(image["storage_path"], 3600)
        item["images"].append({
            "id": image["id"],
            "url": signed.get("signedURL") or signed.get("signedUrl"),
            "sort_order": image["sort_order"],
        })
    item["vehicle_type"] = vehicle_type
    return item


def _get_owned_listing(vehicle_type: str, vehicle_id: str, user_id: str) -> dict[str, object]:
    _check_vehicle_type(vehicle_type)
    response = (
        get_supabase()
        .table(vehicle_type)
        .select("*")
        .eq("id", vehicle_id)
        .eq("profile_id", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Listing not found.")
    return response.data[0]


def is_payment_successful(vehicle_type: str, listing: dict[str, object]) -> bool:
    """Temporary Payrexx placeholder. Replace this body with verified payment data."""
    _check_vehicle_type(vehicle_type)
    return True


def get_payment_status(vehicle_type: str, vehicle_id: str, user_id: str) -> dict[str, object]:
    listing = _get_owned_listing(vehicle_type, vehicle_id, user_id)
    successful = listing.get("payment_status") == "paid" or is_payment_successful(vehicle_type, listing)

    if successful and listing.get("payment_status") != "paid":
        get_supabase().table(vehicle_type).update({"payment_status": "paid"}).eq("id", vehicle_id).eq("profile_id", user_id).execute()

    return {"successful": successful, "payment_status": "paid" if successful else "pending"}


def publish_listing(vehicle_type: str, vehicle_id: str, user_id: str) -> dict[str, object]:
    listing = _get_owned_listing(vehicle_type, vehicle_id, user_id)
    if listing.get("status") == "active":
        return listing
    if listing.get("status") != "draft":
        raise HTTPException(status_code=409, detail="Only draft listings can be published.")
    if listing.get("payment_status") != "paid" and not is_payment_successful(vehicle_type, listing):
        raise HTTPException(status_code=402, detail="Payment has not been completed.")

    response = (
        get_supabase()
        .table(vehicle_type)
        .update({
            "status": "active",
            "payment_status": "paid",
            "paid_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", vehicle_id)
        .eq("profile_id", user_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=409, detail="Listing could not be published.")
    return response.data[0]


def reorder_images(vehicle_type: str, vehicle_id: str, user_id: str, image_ids: list[str]) -> list[dict[str, object]]:
    _check_vehicle_type(vehicle_type)
    supabase = get_supabase()
    listing_response = (
        supabase.table(vehicle_type)
        .select("id")
        .eq("id", vehicle_id)
        .eq("profile_id", user_id)
        .limit(1)
        .execute()
    )
    if not listing_response.data:
        raise HTTPException(status_code=403, detail="Only the listing owner can reorder its images.")

    image_response = (
        supabase.table("vehicle_images")
        .select("id")
        .eq("vehicle_type", vehicle_type)
        .eq("vehicle_id", vehicle_id)
        .eq("profile_id", user_id)
        .execute()
    )
    existing_ids = {image["id"] for image in image_response.data or []}
    if len(image_ids) != len(set(image_ids)) or set(image_ids) != existing_ids:
        raise HTTPException(status_code=400, detail="The image order must contain every listing image exactly once.")

    for sort_order, image_id in enumerate(image_ids):
        supabase.table("vehicle_images").update({"sort_order": sort_order}).eq("id", image_id).eq("profile_id", user_id).execute()

    return [{"id": image_id, "sort_order": sort_order} for sort_order, image_id in enumerate(image_ids)]


def list_profile_listings(user_id: str) -> list[dict[str, object]]:
    supabase = get_supabase()
    items: list[dict[str, object]] = []

    for vehicle_type in sorted(VALID_TYPES):
        response = (
            supabase.table(vehicle_type)
            .select("*")
            .eq("profile_id", user_id)
            .execute()
        )
        for item in response.data or []:
            item["vehicle_type"] = vehicle_type
            item["images"] = []
            items.append(item)

    image_response = (
        supabase.table("vehicle_images")
        .select("vehicle_type, vehicle_id, storage_path, sort_order")
        .eq("profile_id", user_id)
        .order("sort_order")
        .execute()
    )
    items_by_vehicle = {(item["vehicle_type"], item["id"]): item for item in items}
    for image in image_response.data or []:
        item = items_by_vehicle.get((image["vehicle_type"], image["vehicle_id"]))
        if item is None:
            continue
        signed = supabase.storage.from_(BUCKET_NAME).create_signed_url(image["storage_path"], 3600)
        item["images"].append({
            "url": signed.get("signedURL") or signed.get("signedUrl"),
            "sort_order": image["sort_order"],
        })

    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)
