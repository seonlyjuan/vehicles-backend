from datetime import datetime, timezone

from supabase import Client

from app.models.user import User


def user_exists(supabase: Client, google_id: str) -> bool:
    response = supabase.table("users").select("google_id").eq("google_id", google_id).limit(1).execute()
    return bool(response.data)


def upsert_user(supabase: Client, user: User) -> None:
    supabase.table("users").upsert({**user.model_dump(), "last_login_at": datetime.now(timezone.utc).isoformat()}, on_conflict="google_id").execute()
