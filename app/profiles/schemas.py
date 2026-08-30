from typing import Literal

from pydantic import BaseModel, Field, model_validator


class UsernameUpdate(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_]{3,30}$")


class SellerProfileUpdate(BaseModel):
    seller_type: Literal["private", "dealer"]
    company_name: str | None = Field(default=None, min_length=2, max_length=160)
    business_address: str | None = Field(default=None, min_length=3, max_length=200)
    business_postal_code: str | None = Field(default=None, pattern=r"^[1-9][0-9]{3}$")
    business_locality: str | None = Field(default=None, min_length=1, max_length=120)
    business_canton: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    uid_number: str | None = Field(default=None, max_length=30)
    commercial_register_number: str | None = Field(default=None, max_length=60)
    business_email: str | None = Field(default=None, min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    business_phone: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def require_dealer_identity(self):
        if self.seller_type == "dealer":
            required = (
                self.company_name,
                self.business_address,
                self.business_postal_code,
                self.business_locality,
                self.business_canton,
                self.uid_number,
                self.business_email,
                self.business_phone,
            )
            if not all(required):
                raise ValueError("Für Händler müssen vollständige Geschäftsdaten angegeben werden.")
        return self


class AccountDeletionRequest(BaseModel):
    confirmation: Literal["KONTO LÖSCHEN"]

