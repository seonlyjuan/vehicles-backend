from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user_id
from app.db.supabase import get_supabase

router = APIRouter(prefix="/profile", tags=["profile"])


class UsernameUpdate(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_]{3,30}$")


@router.get("")
def get_profile(user_id: str = Depends(get_current_user_id)) -> dict[str, object]:
    response = get_supabase().table("profiles").select("username").eq("id", user_id).limit(1).execute()
    return response.data[0] if response.data else {"username": None}


@router.put("/username")
def update_username(payload: UsernameUpdate, user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    try:
        response = get_supabase().table("profiles").upsert(
            {"id": user_id, "username": payload.username.lower()}, on_conflict="id"
        ).execute()
    except Exception as exc:
        if "23505" in str(exc):
            raise HTTPException(status_code=409, detail="Dieser Username ist bereits vergeben.") from exc
        raise
    return {"username": response.data[0]["username"]}
