from pydantic import BaseModel


class GoogleCredential(BaseModel):
    credential: str


class AuthenticatedUser(BaseModel):
    id: str
    email: str
    name: str
    picture: str | None = None


class GoogleLoginResponse(BaseModel):
    new_user: bool
    user: AuthenticatedUser
