from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.supabase import get_supabase
from app.messages.access import get_participating_conversation
from app.messages.schemas import MAX_MESSAGE_LENGTH
from app.safety.access import ensure_users_can_interact
from app.vehicles.access import check_vehicle_type

MAX_CONVERSATIONS = 50
MAX_MESSAGES = 100


def start_conversation(vehicle_type: str, listing_id: str, buyer_id: str) -> dict[str, object]:
    check_vehicle_type(vehicle_type)
    supabase = get_supabase()
    listing_response = (
        supabase.table(vehicle_type).select("id, profile_id, title, status")
        .eq("id", listing_id).limit(1).execute()
    )
    if not listing_response.data or listing_response.data[0].get("status") != "active":
        raise HTTPException(status_code=404, detail="Active listing not found.")

    listing = listing_response.data[0]
    seller_id = listing["profile_id"]
    if seller_id == buyer_id:
        raise HTTPException(status_code=400, detail="You cannot contact yourself about your own listing.")
    ensure_users_can_interact(buyer_id, seller_id)

    existing = (
        supabase.table("conversations").select("*")
        .eq("vehicle_type", vehicle_type).eq("listing_id", listing_id)
        .eq("buyer_id", buyer_id).eq("seller_id", seller_id).limit(1).execute()
    )
    if existing.data:
        conversation = existing.data[0]
        if conversation.get("status") == "closed":
            reopened = supabase.table("conversations").update({
                "status": "active",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", conversation["id"]).execute()
            return reopened.data[0]
        return conversation

    response = supabase.table("conversations").insert({
        "vehicle_type": vehicle_type,
        "listing_id": listing_id,
        "buyer_id": buyer_id,
        "seller_id": seller_id,
    }).execute()
    return response.data[0]


def list_conversations(user_id: str) -> list[dict[str, object]]:
    response = (
        get_supabase().table("conversations").select("*")
        .or_(f"buyer_id.eq.{user_id},seller_id.eq.{user_id}")
        .order("updated_at", desc=True).limit(MAX_CONVERSATIONS).execute()
    )
    return _enrich_conversations(response.data or [], user_id)


def get_messages(conversation_id: str, user_id: str) -> dict[str, object]:
    conversation = get_participating_conversation(conversation_id, user_id)
    response = (
        get_supabase().table("messages").select("id, sender_id, content, created_at")
        .eq("conversation_id", conversation_id).order("created_at", desc=True)
        .limit(MAX_MESSAGES).execute()
    )
    _mark_as_read(conversation_id, user_id)
    return {
        "conversation": _enrich_conversations([conversation], user_id)[0],
        "messages": list(reversed(response.data or [])),
        "max_message_length": MAX_MESSAGE_LENGTH,
    }


def send_message(conversation_id: str, user_id: str, content: str) -> dict[str, object]:
    conversation = get_participating_conversation(conversation_id, user_id)
    if conversation.get("status") != "active":
        raise HTTPException(status_code=409, detail="This conversation is closed.")
    other_user_id = conversation["seller_id"] if conversation["buyer_id"] == user_id else conversation["buyer_id"]
    if not other_user_id:
        raise HTTPException(status_code=409, detail="Das andere Konto wurde gelöscht.")
    ensure_users_can_interact(user_id, other_user_id)

    supabase = get_supabase()
    response = supabase.table("messages").insert({
        "conversation_id": conversation_id,
        "sender_id": user_id,
        "content": content,
    }).execute()
    supabase.table("conversations").update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", conversation_id).execute()
    return response.data[0]


def _enrich_conversations(
    conversations: list[dict[str, object]],
    user_id: str,
) -> list[dict[str, object]]:
    if not conversations:
        return []

    supabase = get_supabase()
    other_user_ids = {
        conversation["seller_id"]
        if conversation["buyer_id"] == user_id
        else conversation["buyer_id"]
        for conversation in conversations
        if (conversation["seller_id"] if conversation["buyer_id"] == user_id else conversation["buyer_id"])
    }
    profile_response = (
        supabase.table("profiles").select("id, username")
        .in_("id", list(other_user_ids)).execute()
        if other_user_ids else None
    )
    profiles = profile_response.data or [] if profile_response else []
    usernames = {profile["id"]: profile.get("username") for profile in profiles}

    listing_titles: dict[tuple[str, object], str | None] = {}
    vehicle_types = {str(conversation["vehicle_type"]) for conversation in conversations}
    for vehicle_type in vehicle_types:
        listing_ids = [
            conversation["listing_id"]
            for conversation in conversations
            if conversation["vehicle_type"] == vehicle_type
        ]
        listing_response = (
            supabase.table(vehicle_type).select("id, title")
            .in_("id", listing_ids).execute()
        )
        listing_titles.update({
            (vehicle_type, listing["id"]): listing.get("title")
            for listing in listing_response.data or []
        })

    conversation_ids = [conversation["id"] for conversation in conversations]
    notification_response = (
        supabase.table("message_notifications").select("conversation_id")
        .eq("recipient_id", user_id).is_("read_at", "null")
        .in_("conversation_id", conversation_ids).execute()
    )
    unread_conversation_ids = {
        notification["conversation_id"]
        for notification in notification_response.data or []
    }

    result = []
    for conversation in conversations:
        other_user_id = (
            conversation["seller_id"]
            if conversation["buyer_id"] == user_id
            else conversation["buyer_id"]
        )
        listing_key = (str(conversation["vehicle_type"]), conversation["listing_id"])
        result.append({
            **conversation,
            "other_user_id": other_user_id,
            "other_user": usernames.get(other_user_id),
            "listing_title": listing_titles.get(listing_key) or "Gelöschtes Inserat",
            "has_unread": conversation["id"] in unread_conversation_ids,
        })
    return result


def _mark_as_read(conversation_id: str, user_id: str) -> None:
    (
        get_supabase().table("message_notifications")
        .update({"read_at": datetime.now(timezone.utc).isoformat()})
        .eq("recipient_id", user_id)
        .eq("conversation_id", conversation_id)
        .is_("read_at", "null")
        .execute()
    )
