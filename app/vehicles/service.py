import uuid

from fastapi import HTTPException, UploadFile

from app.db.supabase import get_supabase

BUCKET_NAME = "vehicles-images"
VALID_TYPES = {"bicycles", "cars", "motorbikes"}
VALID_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 6


def _check_vehicle_type(vehicle_type: str) -> None:
    if vehicle_type not in VALID_TYPES:
        raise HTTPException(status_code=404, detail="Unknown vehicle type.")


def create_listing(vehicle_type: str, user_id: str, payload: dict[str, object]) -> dict[str, object]:
    _check_vehicle_type(vehicle_type)
    if vehicle_type == "bicycles":
        payload.pop("model", None)
        payload.pop("year", None)

    response = get_supabase().table(vehicle_type).insert({**payload, "profile_id": user_id}).execute()
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


def list_listings(vehicle_type: str, page: int, per_page: int) -> dict[str, object]:
    _check_vehicle_type(vehicle_type)
    supabase = get_supabase()
    start = (page - 1) * per_page
    response = supabase.table(vehicle_type).select("*", count="exact").order("created_at", desc=True).range(start, start + per_page - 1).execute()
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
