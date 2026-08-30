from fastapi import HTTPException

from app.db.supabase import get_supabase


def ensure_users_can_interact(first_user_id: str, second_user_id: str) -> None:
    response = (
        get_supabase().table("user_blocks").select("id")
        .or_(
            f"and(blocker_id.eq.{first_user_id},blocked_user_id.eq.{second_user_id}),"
            f"and(blocker_id.eq.{second_user_id},blocked_user_id.eq.{first_user_id})"
        ).limit(1).execute()
    )
    if response.data:
        raise HTTPException(status_code=403, detail="Zwischen diesen Konten sind keine Nachrichten möglich.")

