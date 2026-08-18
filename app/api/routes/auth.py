from fastapi import APIRouter

from app.schemas.auth import GoogleCredential, GoogleLoginResponse
from app.services.auth_service import authenticate_google

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/google", response_model=GoogleLoginResponse)
def authenticate_with_google(payload: GoogleCredential) -> GoogleLoginResponse:
    return authenticate_google(payload.credential)
