from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.auth import get_current_user_id
from app.vehicles.image_validation import validate_image_count
from app.vehicles.image_service import add_images, reorder_images
from app.vehicles.rate_limits import (
    check_image_upload_limit,
    create_limited_user,
    image_order_limited_user,
    payment_limited_user,
    publish_limited_user,
    read_limited_user,
)
from app.vehicles.schemas import ImageOrderUpdate, VehicleCreate
from app.vehicles.service import (
    create_listing,
    get_filter_metadata,
    get_listing,
    get_payment_status,
    list_listings,
    publish_listing,
)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/{vehicle_type}")
def get_listings(
    vehicle_type: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=30),
    brand: str | None = Query(default=None, max_length=80),
    model: str | None = Query(default=None, max_length=80),
    price_min: float | None = Query(default=None, ge=0),
    price_max: float | None = Query(default=None, ge=0),
    year_min: int | None = Query(default=None, ge=1886, le=2100),
    year_max: int | None = Query(default=None, ge=1886, le=2100),
    power_min: int | None = Query(default=None, ge=0, le=5000),
    power_max: int | None = Query(default=None, ge=0, le=5000),
    _: str = Depends(read_limited_user),
) -> dict[str, object]:
    filters = {
        "brand": brand,
        "model": model,
        "price_min": price_min,
        "price_max": price_max,
        "year_min": year_min,
        "year_max": year_max,
        "power_min": power_min,
        "power_max": power_max,
    }
    return list_listings(vehicle_type, page, per_page, filters)


@router.get("/{vehicle_type}/filters")
def get_listing_filters(vehicle_type: str, _: str = Depends(read_limited_user)) -> dict[str, object]:
    return get_filter_metadata(vehicle_type)


@router.get("/{vehicle_type}/{vehicle_id}")
def get_listing_detail(vehicle_type: str, vehicle_id: str, user_id: str = Depends(read_limited_user)) -> dict[str, object]:
    return get_listing(vehicle_type, vehicle_id, user_id)


@router.get("/{vehicle_type}/{vehicle_id}/payment-status")
def get_listing_payment_status(vehicle_type: str, vehicle_id: str, user_id: str = Depends(payment_limited_user)) -> dict[str, object]:
    return get_payment_status(vehicle_type, vehicle_id, user_id)


@router.post("/{vehicle_type}/{vehicle_id}/publish")
def post_publish_listing(vehicle_type: str, vehicle_id: str, user_id: str = Depends(publish_limited_user)) -> dict[str, object]:
    return publish_listing(vehicle_type, vehicle_id, user_id)


@router.post("/{vehicle_type}")
def post_listing(vehicle_type: str, payload: VehicleCreate, user_id: str = Depends(create_limited_user)) -> dict[str, object]:
    return create_listing(vehicle_type, user_id, payload.model_dump())


@router.post("/{vehicle_type}/{vehicle_id}/images")
async def post_images(vehicle_type: str, vehicle_id: str, files: list[UploadFile] = File(...), user_id: str = Depends(get_current_user_id)) -> list[dict[str, object]]:
    validate_image_count(files)
    check_image_upload_limit(user_id, len(files))
    return await add_images(vehicle_type, vehicle_id, user_id, files)


@router.put("/{vehicle_type}/{vehicle_id}/images/order")
def put_image_order(vehicle_type: str, vehicle_id: str, payload: ImageOrderUpdate, user_id: str = Depends(image_order_limited_user)) -> list[dict[str, object]]:
    return reorder_images(vehicle_type, vehicle_id, user_id, payload.image_ids)
