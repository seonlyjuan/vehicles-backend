from app.db.supabase import get_supabase
from app.vehicles.constants import BUCKET_NAME


def add_listing_images(items: list[dict[str, object]]) -> None:
    if not items:
        return
    supabase = get_supabase()
    grouped_ids: dict[str, list[object]] = {}
    items_by_key: dict[tuple[str, object], dict[str, object]] = {}
    for item in items:
        item["images"] = []
        vehicle_type = str(item["vehicle_type"])
        grouped_ids.setdefault(vehicle_type, []).append(item["id"])
        items_by_key[(vehicle_type, item["id"])] = item

    bucket = supabase.storage.from_(BUCKET_NAME)
    for vehicle_type, vehicle_ids in grouped_ids.items():
        response = (
            supabase.table("vehicle_images").select("id, vehicle_id, storage_path, sort_order")
            .eq("vehicle_type", vehicle_type).in_("vehicle_id", vehicle_ids)
            .order("sort_order").execute()
        )
        stored_images = response.data or []
        signed_items = bucket.create_signed_urls(
            [stored_image["storage_path"] for stored_image in stored_images], 3600
        ) if stored_images else []
        urls = {
            signed.get("path"): signed.get("signedURL") or signed.get("signedUrl")
            for signed in signed_items
        }
        for stored_image in stored_images:
            item = items_by_key.get((vehicle_type, stored_image["vehicle_id"]))
            if item is None:
                continue
            item["images"].append({
                "id": stored_image["id"],
                "url": urls.get(stored_image["storage_path"]),
                "sort_order": stored_image["sort_order"],
            })
