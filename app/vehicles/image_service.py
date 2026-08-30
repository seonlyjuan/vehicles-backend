import uuid

from fastapi import HTTPException, UploadFile

from app.db.supabase import get_supabase
from app.vehicles.access import check_vehicle_type, get_owned_listing
from app.vehicles.constants import BUCKET_NAME
from app.vehicles.image_validation import MAX_IMAGES, prepare_images
from app.vehicles.storage_service import remove_vehicle_files


async def add_images(vehicle_type: str, vehicle_id: str, user_id: str, files: list[UploadFile]) -> list[dict[str, object]]:
    check_vehicle_type(vehicle_type)
    get_owned_listing(vehicle_type, vehicle_id, user_id)
    supabase = get_supabase()
    existing_response = (
        supabase.table("vehicle_images").select("id", count="exact")
        .eq("vehicle_type", vehicle_type).eq("vehicle_id", vehicle_id).execute()
    )
    existing_count = existing_response.count or 0
    if existing_count + len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"A listing can have at most {MAX_IMAGES} images.")

    processed_files = await prepare_images(files)
    uploaded_paths: list[str] = []
    images: list[dict[str, object]] = []
    try:
        for offset, image in enumerate(processed_files):
            path = f"{user_id}/{vehicle_type}/{vehicle_id}/{uuid.uuid4()}.{image.extension}"
            supabase.storage.from_(BUCKET_NAME).upload(path, image.content, {"content-type": image.content_type})
            uploaded_paths.append(path)
            response = supabase.table("vehicle_images").insert({
                "profile_id": user_id,
                "vehicle_type": vehicle_type,
                "vehicle_id": vehicle_id,
                "storage_path": path,
                "content_type": image.content_type,
                "sort_order": existing_count + offset,
            }).execute()
            images.append(response.data[0])
    except Exception:
        if uploaded_paths:
            remove_vehicle_files(uploaded_paths)
        for image in images:
            supabase.table("vehicle_images").delete().eq("id", image["id"]).eq("profile_id", user_id).execute()
        raise
    return images


def reorder_images(vehicle_type: str, vehicle_id: str, user_id: str, image_ids: list[str]) -> list[dict[str, object]]:
    get_owned_listing(vehicle_type, vehicle_id, user_id)
    supabase = get_supabase()
    response = (
        supabase.table("vehicle_images").select("id")
        .eq("vehicle_type", vehicle_type).eq("vehicle_id", vehicle_id).eq("profile_id", user_id).execute()
    )
    existing_ids = {image["id"] for image in response.data or []}
    if len(image_ids) != len(set(image_ids)) or set(image_ids) != existing_ids:
        raise HTTPException(status_code=400, detail="The image order must contain every listing image exactly once.")

    for sort_order, image_id in enumerate(image_ids):
        supabase.table("vehicle_images").update({"sort_order": sort_order}).eq("id", image_id).eq("profile_id", user_id).execute()
    return [{"id": image_id, "sort_order": sort_order} for sort_order, image_id in enumerate(image_ids)]


def delete_listing_images(vehicle_type: str, vehicle_id: str, user_id: str) -> None:
    get_owned_listing(vehicle_type, vehicle_id, user_id)
    supabase = get_supabase()
    response = (
        supabase.table("vehicle_images").select("id, storage_path")
        .eq("vehicle_type", vehicle_type).eq("vehicle_id", vehicle_id)
        .eq("profile_id", user_id).execute()
    )
    images = response.data or []
    paths = [image["storage_path"] for image in images]
    if paths:
        remove_vehicle_files(paths)
    if images:
        supabase.table("vehicle_images").delete().eq("vehicle_type", vehicle_type).eq(
            "vehicle_id", vehicle_id
        ).eq("profile_id", user_id).execute()
