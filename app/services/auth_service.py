import logging
from collections.abc import Mapping

from fastapi import HTTPException
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings
from app.crud.users import upsert_user, user_exists
from app.db.supabase import get_supabase
from app.models.user import User
from app.schemas.auth import AuthenticatedUser, GoogleLoginResponse

logger = logging.getLogger(__name__)


def authenticate_google(credential: str) -> GoogleLoginResponse:
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID ist noch nicht konfiguriert.")
    try:
        token_data: Mapping[str, object] = id_token.verify_oauth2_token(credential, requests.Request(), settings.google_client_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Ungültige Google-Anmeldung.") from exc
    if not token_data.get("email_verified"):
        raise HTTPException(status_code=403, detail="Die Google-E-Mail-Adresse ist nicht verifiziert.")

    user = User(google_id=str(token_data["sub"]), email=str(token_data["email"]), name=str(token_data.get("name", token_data["email"])), picture=str(token_data["picture"]) if token_data.get("picture") else None)
    try:
        supabase = get_supabase()
        is_new_user = not user_exists(supabase, user.google_id)
        upsert_user(supabase, user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Supabase user upsert failed")
        raise HTTPException(status_code=503, detail="Benutzerkonto konnte nicht in Supabase gespeichert werden.") from exc

    return GoogleLoginResponse(new_user=is_new_user, user=AuthenticatedUser(id=user.google_id, email=user.email, name=user.name, picture=user.picture))
