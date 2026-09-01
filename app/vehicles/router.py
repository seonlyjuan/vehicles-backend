from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.core.security.authentication import get_active_user_id
from app.vehicles.filters import get_filter_metadata
from app.vehicles.image_validation import validate_image_count
from app.vehicles.image_service import add_images, reorder_images
from app.vehicles.rate_limits import (
    check_image_upload_limit,
    create_limited_user,
    delete_limited_user,
    edit_limited_user,
    image_order_limited_user,
    payment_limited_user,
    publish_limited_user,
    read_limited_user,
    status_limited_user,
)
from app.vehicles.schemas import (
    ImageOrderUpdate,
    ListingPublishRequest,
    ListingStatusUpdate,
    VehicleCreate,
    VehicleUpdate,
)
from app.vehicles.lifecycle import change_listing_status, delete_listing, publish_listing, update_listing
from app.vehicles.listing_service import (
    create_listing,
    get_listing,
    list_listings,
)
from app.vehicles.payment_service import get_payment_status

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
    canton: str | None = Query(default=None, pattern=r"^[A-Z]{2}$"),
    postal_code: str | None = Query(default=None, pattern=r"^[1-9][0-9]{3}$"),
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
        "canton": canton,
        "postal_code": postal_code,
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
def post_publish_listing(
    vehicle_type: str,
    vehicle_id: str,
    payload: ListingPublishRequest,
    user_id: str = Depends(publish_limited_user),
) -> dict[str, object]:
    return publish_listing(vehicle_type, vehicle_id, user_id, payload.terms_version)


@router.post("/{vehicle_type}")
def post_listing(vehicle_type: str, payload: VehicleCreate, user_id: str = Depends(create_limited_user)) -> dict[str, object]:
    return create_listing(vehicle_type, user_id, payload.model_dump(mode="json"))


@router.patch("/{vehicle_type}/{vehicle_id}")
def patch_listing(
    vehicle_type: str,
    vehicle_id: str,
    payload: VehicleUpdate,
    user_id: str = Depends(edit_limited_user),
) -> dict[str, object]:
    return update_listing(vehicle_type, vehicle_id, user_id, payload.model_dump(mode="json", exclude_unset=True))


@router.patch("/{vehicle_type}/{vehicle_id}/status")
def patch_listing_status(
    vehicle_type: str,
    vehicle_id: str,
    payload: ListingStatusUpdate,
    user_id: str = Depends(status_limited_user),
) -> dict[str, object]:
    return change_listing_status(vehicle_type, vehicle_id, user_id, payload.action)


@router.delete("/{vehicle_type}/{vehicle_id}", status_code=204)
def delete_owned_listing(
    vehicle_type: str,
    vehicle_id: str,
    user_id: str = Depends(delete_limited_user),
) -> Response:
    delete_listing(vehicle_type, vehicle_id, user_id)
    return Response(status_code=204)


@router.post("/{vehicle_type}/{vehicle_id}/images")
async def post_images(vehicle_type: str, vehicle_id: str, files: list[UploadFile] = File(...), user_id: str = Depends(get_active_user_id)) -> list[dict[str, object]]:
    validate_image_count(files)
    check_image_upload_limit(user_id, len(files))
    return await add_images(vehicle_type, vehicle_id, user_id, files)


@router.put("/{vehicle_type}/{vehicle_id}/images/order")
def put_image_order(vehicle_type: str, vehicle_id: str, payload: ImageOrderUpdate, user_id: str = Depends(image_order_limited_user)) -> list[dict[str, object]]:
    return reorder_images(vehicle_type, vehicle_id, user_id, payload.image_ids)
