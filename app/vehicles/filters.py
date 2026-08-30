from fastapi import HTTPException

from app.vehicles.access import check_vehicle_type

VEHICLE_FILTERS = {
    "bicycles": ("brand", "model", "price", "year"),
    "cars": ("brand", "model", "price", "year", "power"),
    "motorbikes": ("brand", "model", "price", "year", "power"),
}
FILTER_DEFINITIONS = {
    "brand": {"name": "brand", "label": "Marke", "type": "text"},
    "model": {"name": "model", "label": "Modell", "type": "text"},
    "price": {"name": "price", "label": "Preis", "type": "range", "unit": "CHF", "min": 0},
    "year": {"name": "year", "label": "Jahr", "type": "range", "min": 1886, "max": 2100},
    "power": {"name": "power", "label": "Leistung", "type": "range", "unit": "PS", "min": 0, "max": 5000},
}


def get_filter_metadata(vehicle_type: str) -> dict[str, object]:
    check_vehicle_type(vehicle_type)
    return {
        "vehicle_type": vehicle_type,
        "characteristics": [FILTER_DEFINITIONS[name] for name in VEHICLE_FILTERS[vehicle_type]],
    }


def validate_filters(vehicle_type: str, filters: dict[str, object]) -> None:
    allowed = VEHICLE_FILTERS[vehicle_type]
    for name in ("price", "year", "power"):
        minimum = filters.get(f"{name}_min")
        maximum = filters.get(f"{name}_max")
        if name not in allowed and (minimum is not None or maximum is not None):
            raise HTTPException(status_code=422, detail=f"Filter '{name}' is not available for {vehicle_type}.")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise HTTPException(status_code=422, detail=f"{name}_min must not be greater than {name}_max.")

