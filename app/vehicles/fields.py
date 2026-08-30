PUBLIC_LISTING_FIELDS = (
    "id, profile_id, title, brand, model, year, power, price, description, status, "
    "created_at, updated_at, postal_code, locality, canton, condition, known_defects, "
    "mileage, first_registration, expires_at"
)

PUBLIC_LISTING_FIELD_NAMES = {field.strip() for field in PUBLIC_LISTING_FIELDS.split(",")}


def public_listing_fields(vehicle_type: str) -> str:
    if vehicle_type == "bicycles":
        return ", ".join(
            field.strip() for field in PUBLIC_LISTING_FIELDS.split(",")
            if field.strip() != "power"
        )
    return PUBLIC_LISTING_FIELDS


def public_listing_data(listing: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in listing.items() if key in PUBLIC_LISTING_FIELD_NAMES}
