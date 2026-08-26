from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase import get_supabase

security = HTTPBearer(auto_error=False)


def get_current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing access token.")

    try:
        user = get_supabase().auth.get_user(credentials.credentials).user
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.") from exc

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.")
    return str(user.id)
