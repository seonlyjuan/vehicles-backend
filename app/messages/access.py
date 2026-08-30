from fastapi import HTTPException

from app.db.supabase import get_supabase


def get_participating_conversation(conversation_id: str, user_id: str) -> dict[str, object]:
    response = (
        get_supabase().table("conversations").select("*")
        .eq("id", conversation_id).limit(1).execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    conversation = response.data[0]
    if user_id not in (conversation["buyer_id"], conversation["seller_id"]):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation
