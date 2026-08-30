from fastapi import HTTPException

from app.db.supabase import get_supabase
from app.moderation.audit import record_action, utc_now
from app.moderation.schemas import DealerDecision
from app.notifications.service import create_notification


def list_pending_dealers() -> list[dict[str, object]]:
    response = (
        get_supabase().table("profiles").select(
            "id, username, company_name, business_address, business_postal_code, business_locality, "
            "business_canton, uid_number, commercial_register_number, business_email, business_phone, "
            "dealer_verification_status"
        ).eq("seller_type", "dealer").eq("dealer_verification_status", "pending").execute()
    )
    return response.data or []


def decide_dealer(user_id: str, moderator_id: str, payload: DealerDecision) -> dict[str, object]:
    values: dict[str, object] = {
        "dealer_verification_status": payload.status,
        "dealer_verified_at": utc_now() if payload.status == "verified" else None,
    }
    if payload.status == "suspended":
        values["account_status"] = "suspended"
    response = (
        get_supabase().table("profiles").update(values)
        .eq("id", user_id).eq("seller_type", "dealer").execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Händlerprofil nicht gefunden.")
    record_action(moderator_id, "decide_dealer", "user", user_id, payload.decision, {"status": payload.status})
    create_notification(
        user_id,
        "dealer_review",
        "Händlerprüfung abgeschlossen",
        payload.decision,
        f"dealer-review:{user_id}:{payload.status}:{utc_now()}",
        "/profile/settings",
    )
    return response.data[0]

