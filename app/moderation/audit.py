from datetime import datetime, timezone

from app.db.supabase import get_supabase


def record_action(
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str,
    reason: str,
    metadata: dict[str, object],
) -> None:
    get_supabase().table("moderation_actions").insert({
        "actor_id": actor_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason,
        "metadata": metadata,
    }).execute()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

