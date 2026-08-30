import base64
import binascii
import json
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase import get_supabase

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing access token.")

    try:
        user = get_supabase().auth.get_user(credentials.credentials).user
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.") from exc

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.")
    return str(user.id)


def get_active_user_id(user_id: str = Depends(get_current_user_id)) -> str:
    response = (
        get_supabase().table("profiles").select("account_status")
        .eq("id", user_id).limit(1).execute()
    )
    if response.data and response.data[0].get("account_status") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dieses Konto ist nicht aktiv.")
    return user_id


def require_recent_authentication(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user_id: str = Depends(get_active_user_id),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing access token.")
    try:
        encoded_payload = credentials.credentials.split(".")[1]
        encoded_payload += "=" * (-len(encoded_payload) % 4)
        issued_at = int(json.loads(base64.urlsafe_b64decode(encoded_payload))["iat"])
    except (IndexError, KeyError, TypeError, ValueError, binascii.Error, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token.") from exc
    if time.time() - issued_at > 10 * 60:
        raise HTTPException(status_code=401, detail="Bitte melde dich erneut an, bevor du das Konto löschst.")
    return user_id
