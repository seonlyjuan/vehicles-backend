from pydantic import BaseModel


class User(BaseModel):
    google_id: str
    email: str
    name: str
    picture: str | None = None
