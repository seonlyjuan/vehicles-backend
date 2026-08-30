from fastapi import Depends, HTTPException

from app.core.security.authentication import get_active_user_id
from app.db.supabase import get_supabase


def require_moderator(user_id: str = Depends(get_active_user_id)) -> str:
    response = (
        get_supabase().table("profiles").select("platform_role")
        .eq("id", user_id).limit(1).execute()
    )
    role = response.data[0].get("platform_role") if response.data else "user"
    if role not in {"moderator", "admin"}:
        raise HTTPException(status_code=403, detail="Moderator access required.")
    return user_id


def require_admin(user_id: str = Depends(get_active_user_id)) -> str:
    response = (
        get_supabase().table("profiles").select("platform_role")
        .eq("id", user_id).limit(1).execute()
    )
    role = response.data[0].get("platform_role") if response.data else "user"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user_id
