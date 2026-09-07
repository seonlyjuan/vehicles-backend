from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class PlaceholderWebhookEvent(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=200)
    vehicle_type: Literal["bicycles", "cars", "motorbikes"]
    listing_id: str = Field(min_length=1, max_length=100)
    status: Literal["paid", "failed", "refunded"]
    amount: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    currency: Literal["CHF"] = "CHF"


class RefundRequestCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class RefundDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = Field(min_length=3, max_length=1000)
