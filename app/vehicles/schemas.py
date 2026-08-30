from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class VehicleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    brand: str = Field(min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    year: int | None = Field(default=None, ge=1886, le=2100)
    power: int | None = Field(default=None, ge=0, le=5000)
    price: float = Field(ge=0)
    description: str | None = Field(default=None, max_length=5000)
    postal_code: str = Field(pattern=r"^[1-9][0-9]{3}$")
    locality: str = Field(min_length=1, max_length=120)
    canton: str = Field(pattern=r"^[A-Z]{2}$")
    condition: Literal["new", "used", "damaged"] = "used"
    known_defects: str | None = Field(default=None, max_length=5000)
    mileage: int | None = Field(default=None, ge=0, le=10_000_000)
    first_registration: date | None = None


class VehicleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    brand: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    year: int | None = Field(default=None, ge=1886, le=2100)
    power: int | None = Field(default=None, ge=0, le=5000)
    price: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=5000)
    postal_code: str | None = Field(default=None, pattern=r"^[1-9][0-9]{3}$")
    locality: str | None = Field(default=None, min_length=1, max_length=120)
    canton: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    condition: Literal["new", "used", "damaged"] | None = None
    known_defects: str | None = Field(default=None, max_length=5000)
    mileage: int | None = Field(default=None, ge=0, le=10_000_000)
    first_registration: date | None = None


class ListingStatusUpdate(BaseModel):
    action: Literal["archive", "reactivate", "mark_sold"]


class ImageOrderUpdate(BaseModel):
    image_ids: list[str] = Field(min_length=1, max_length=6)
