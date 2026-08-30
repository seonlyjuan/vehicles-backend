from pydantic import BaseModel, Field, field_validator


class SwissLocation(BaseModel):
    postal_code: str = Field(pattern=r"^[1-9][0-9]{3}$")
    locality: str = Field(min_length=1, max_length=120)
    canton: str = Field(pattern=r"^[A-Z]{2}$")

    @field_validator("postal_code", "locality", "canton")
    @classmethod
    def strip_value(cls, value: str) -> str:
        return value.strip()

