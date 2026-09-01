from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.supabase import get_supabase
from app.vehicles.constants import VALID_TYPES
from app.vehicles.storage_service import remove_vehicle_files


def export_account_data(user_id: str) -> dict[str, object]:
    supabase = get_supabase()
    auth_response = supabase.auth.admin.get_user_by_id(user_id)
    profile = supabase.table("profiles").select("*").eq("id", user_id).limit(1).execute().data
    listings: dict[str, list[dict[str, object]]] = {}
    for vehicle_type in sorted(VALID_TYPES):
        listings[vehicle_type] = (
            supabase.table(vehicle_type).select("*").eq("profile_id", user_id).execute().data or []
        )

    conversations = (
        supabase.table("conversations").select("*")
        .or_(f"buyer_id.eq.{user_id},seller_id.eq.{user_id}").execute().data or []
    )
    conversation_ids = [conversation["id"] for conversation in conversations]
    messages = []
    if conversation_ids:
        messages = (
            supabase.table("messages").select("id, conversation_id, sender_id, content, created_at")
            .in_("conversation_id", conversation_ids).order("created_at").execute().data or []
        )

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": {"id": user_id, "email": auth_response.user.email if auth_response.user else None},
        "profile": profile[0] if profile else None,
        "listings": listings,
        "conversations": conversations,
        "messages": messages,
        "reports": supabase.table("content_reports").select("*").eq("reporter_id", user_id).execute().data or [],
        "blocks": supabase.table("user_blocks").select("*").eq("blocker_id", user_id).execute().data or [],
        "payments": supabase.table("listing_payments").select("*").eq("user_id", user_id).execute().data or [],
        "legal_acceptances": (
            supabase.table("legal_acceptances")
            .select("*, legal_documents(document_type, version, display_version, title, public_path, content_sha256)")
            .eq("user_id", user_id).execute().data or []
        ),
        "notifications": supabase.table("user_notifications").select("*").eq("recipient_id", user_id).execute().data or [],
        "moderation_appeals": supabase.table("moderation_appeals").select("*").eq("appellant_id", user_id).execute().data or [],
    }


def delete_account(user_id: str) -> None:
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("profiles").update({
        "account_status": "deletion_requested",
        "deletion_requested_at": now,
    }).eq("id", user_id).execute()

    try:
        image_response = (
            supabase.table("vehicle_images").select("storage_path")
            .eq("profile_id", user_id).execute()
        )
        storage_paths = [item["storage_path"] for item in image_response.data or []]
        if storage_paths:
            remove_vehicle_files(storage_paths)
        supabase.table("conversations").update({"status": "closed"}).or_(
            f"buyer_id.eq.{user_id},seller_id.eq.{user_id}"
        ).execute()
        supabase.auth.admin.delete_user(user_id)
    except Exception as exc:
        supabase.table("profiles").update({
            "account_status": "active",
            "deletion_requested_at": None,
        }).eq("id", user_id).execute()
        raise HTTPException(status_code=502, detail="Das Konto konnte nicht vollständig gelöscht werden.") from exc

    supabase.table("profiles").delete().eq("id", user_id).execute()
