from fastapi import HTTPException

from app.db.supabase import get_supabase
from app.moderation.audit import record_action, utc_now
from app.moderation.schemas import AppealDecision
from app.notifications.service import create_notification


def list_open_appeals() -> list[dict[str, object]]:
    response = (
        get_supabase().table("moderation_appeals").select("*")
        .eq("status", "open").order("created_at").execute()
    )
    return response.data or []


def decide_appeal(appeal_id: str, moderator_id: str, payload: AppealDecision) -> dict[str, object]:
    existing = (
        get_supabase().table("moderation_appeals").select("*, content_reports(*)")
        .eq("id", appeal_id).eq("status", "open").limit(1).execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Offener Einspruch nicht gefunden.")
    appeal = existing.data[0]
    if payload.status == "accepted":
        _restore_after_appeal(appeal.get("content_reports") or {})
    response = get_supabase().table("moderation_appeals").update({
        "status": payload.status,
        "decision": payload.decision,
        "reviewer_id": moderator_id,
        "reviewed_at": utc_now(),
    }).eq("id", appeal_id).eq("status", "open").execute()
    record_action(moderator_id, "decide_appeal", "appeal", appeal_id, payload.decision, {"status": payload.status})
    if appeal.get("appellant_id"):
        create_notification(
            str(appeal["appellant_id"]),
            "appeal",
            "Einspruch entschieden",
            payload.decision,
            f"appeal:{appeal_id}:{payload.status}",
            "/profile/settings",
        )
    return response.data[0]


def _restore_after_appeal(report: dict[str, object]) -> None:
    if report.get("subject_type") == "listing" and report.get("vehicle_type") and report.get("listing_id"):
        get_supabase().table(str(report["vehicle_type"])).update({
            "status": "archived",
            "suspended_at": None,
            "archived_at": utc_now(),
            "updated_at": utc_now(),
        }).eq("id", report["listing_id"]).eq("status", "suspended").execute()
    user_id = report.get("reported_user_id")
    if user_id:
        get_supabase().table("profiles").update({"account_status": "active"}).eq(
            "id", user_id
        ).eq("account_status", "suspended").execute()

