from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReportReason = Literal[
    "fraud", "stolen_vehicle", "false_information", "dealer_as_private",
    "illegal_content", "copyright", "harassment", "spam", "other",
]


class BlockCreate(BaseModel):
    user_id: str


class ReportCreate(BaseModel):
    subject_type: Literal["listing", "message", "user"]
    vehicle_type: Literal["bicycles", "cars", "motorbikes"] | None = None
    listing_id: str | None = None
    message_id: str | None = None
    reported_user_id: str | None = None
    reason: ReportReason
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_subject(self):
        valid = (
            self.subject_type == "listing" and self.vehicle_type and self.listing_id
        ) or (
            self.subject_type == "message" and self.message_id
        ) or (
            self.subject_type == "user" and self.reported_user_id
        )
        if not valid:
            raise ValueError("Die Angaben passen nicht zum gemeldeten Inhalt.")
        return self


class AppealCreate(BaseModel):
    report_id: str
    statement: str = Field(min_length=10, max_length=2000)
