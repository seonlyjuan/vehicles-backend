from fastapi import APIRouter, Depends

from app.messages.rate_limits import read_limited_user, send_limited_user, start_limited_user
from app.messages.schemas import MessageCreate
from app.messages.service import get_messages, list_conversations, send_message, start_conversation

router = APIRouter(tags=["messages"])


@router.post("/vehicles/{vehicle_type}/{listing_id}/conversation")
def post_conversation(vehicle_type: str, listing_id: str, user_id: str = Depends(start_limited_user)) -> dict[str, object]:
    return start_conversation(vehicle_type, listing_id, user_id)


@router.get("/conversations")
def get_conversations(user_id: str = Depends(read_limited_user)) -> list[dict[str, object]]:
    return list_conversations(user_id)


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str, user_id: str = Depends(read_limited_user)) -> dict[str, object]:
    return get_messages(conversation_id, user_id)


@router.post("/conversations/{conversation_id}/messages")
def post_message(conversation_id: str, payload: MessageCreate, user_id: str = Depends(send_limited_user)) -> dict[str, object]:
    return send_message(conversation_id, user_id, payload.content)
