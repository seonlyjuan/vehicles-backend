from fastapi import APIRouter, Depends, Response

from app.core.security.authentication import require_recent_authentication
from app.profiles.account_service import delete_account, export_account_data
from app.profiles.rate_limits import (
    delete_limited_user,
    export_limited_user,
    read_limited_user,
    update_limited_user,
)
from app.profiles.schemas import AccountDeletionRequest, SellerProfileUpdate, UsernameUpdate
from app.profiles.service import get_profile, update_seller_profile, update_username
from app.vehicles.listing_service import list_profile_listings

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_current_profile(user_id: str = Depends(read_limited_user)) -> dict[str, object]:
    return get_profile(user_id)


@router.get("/listings")
def get_profile_listings(user_id: str = Depends(read_limited_user)) -> list[dict[str, object]]:
    return list_profile_listings(user_id)


@router.put("/username")
def put_username(payload: UsernameUpdate, user_id: str = Depends(update_limited_user)) -> dict[str, str]:
    return update_username(user_id, payload.username)


@router.put("/seller")
def put_seller_profile(
    payload: SellerProfileUpdate,
    user_id: str = Depends(update_limited_user),
) -> dict[str, object]:
    return update_seller_profile(user_id, payload)


@router.get("/export")
def get_account_export(user_id: str = Depends(export_limited_user)) -> dict[str, object]:
    return export_account_data(user_id)


@router.delete("", status_code=204)
def delete_current_account(
    _: AccountDeletionRequest,
    user_id: str = Depends(delete_limited_user),
    __: str = Depends(require_recent_authentication),
) -> Response:
    delete_account(user_id)
    return Response(status_code=204)
