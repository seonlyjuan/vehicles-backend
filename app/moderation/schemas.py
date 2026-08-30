from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ReportDecision(BaseModel):
    outcome: Literal["resolved", "rejected"]
    action: Literal["none", "suspend_listing", "suspend_user"] = "none"
    decision: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def validate_outcome_action(self):
        if self.outcome == "rejected" and self.action != "none":
            raise ValueError("Eine abgelehnte Meldung darf keine Sperraktion auslösen.")
        return self


class DealerDecision(BaseModel):
    status: Literal["verified", "rejected", "suspended"]
    decision: str = Field(min_length=3, max_length=2000)


class AppealDecision(BaseModel):
    status: Literal["accepted", "rejected"]
    decision: str = Field(min_length=3, max_length=2000)
