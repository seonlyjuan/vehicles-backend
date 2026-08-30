from fastapi import APIRouter, Depends, Query

from app.core.security.rate_limiting import RatePolicy, authenticated_rate_limit
from app.locations.service import search_swiss_locations

router = APIRouter(prefix="/locations", tags=["locations"])
location_read_limited_user = authenticated_rate_limit(RatePolicy("locations:read", 60, 60))


@router.get("/postal-codes")
def get_postal_codes(
    query: str = Query(min_length=2, max_length=120),
    _: str = Depends(location_read_limited_user),
) -> list[dict[str, str]]:
    return search_swiss_locations(query)

