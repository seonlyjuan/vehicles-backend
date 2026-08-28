from pydantic import BaseModel, Field


class VehicleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    brand: str = Field(min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    year: int | None = Field(default=None, ge=1886, le=2100)
    power: int | None = Field(default=None, ge=0, le=5000)
    price: float = Field(ge=0)
    description: str | None = None


class ImageOrderUpdate(BaseModel):
    image_ids: list[str] = Field(min_length=1, max_length=6)
