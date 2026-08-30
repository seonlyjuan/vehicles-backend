from datetime import datetime, timezone

from app.db.supabase import get_supabase


def create_notification(
    recipient_id: str,
    kind: str,
    title: str,
    body: str,
    dedupe_key: str,
    link: str | None = None,
) -> None:
    get_supabase().table("user_notifications").upsert({
        "recipient_id": recipient_id,
        "kind": kind,
        "title": title,
        "body": body,
        "link": link,
        "dedupe_key": dedupe_key,
    }, on_conflict="recipient_id,dedupe_key").execute()


def list_notifications(user_id: str) -> dict[str, object]:
    response = (
        get_supabase().table("user_notifications")
        .select("id, kind, title, body, link, created_at, read_at")
        .eq("recipient_id", user_id).order("created_at", desc=True).limit(100).execute()
    )
    items = response.data or []
    return {"items": items, "unread_count": sum(item.get("read_at") is None for item in items)}


def mark_notifications_read(user_id: str, notification_id: str | None = None) -> None:
    query = get_supabase().table("user_notifications").update({
        "read_at": datetime.now(timezone.utc).isoformat(),
    }).eq("recipient_id", user_id).is_("read_at", "null")
    if notification_id:
        query = query.eq("id", notification_id)
    query.execute()

