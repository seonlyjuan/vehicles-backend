from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.supabase import get_supabase
from app.messages.access import get_participating_conversation
from app.safety.schemas import ReportCreate
from app.vehicles.access import check_vehicle_type


def create_block(blocker_id: str, blocked_user_id: str) -> dict[str, object]:
    if blocker_id == blocked_user_id:
        raise HTTPException(status_code=400, detail="Du kannst dich nicht selbst blockieren.")
    profile = get_supabase().table("profiles").select("id").eq("id", blocked_user_id).limit(1).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Nutzer nicht gefunden.")
    response = get_supabase().table("user_blocks").upsert({
        "blocker_id": blocker_id,
        "blocked_user_id": blocked_user_id,
    }, on_conflict="blocker_id,blocked_user_id").execute()
    get_supabase().table("conversations").update({
        "status": "closed",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).or_(
        f"and(buyer_id.eq.{blocker_id},seller_id.eq.{blocked_user_id}),"
        f"and(buyer_id.eq.{blocked_user_id},seller_id.eq.{blocker_id})"
    ).execute()
    return response.data[0]


def list_blocks(user_id: str) -> list[dict[str, object]]:
    response = (
        get_supabase().table("user_blocks").select("id, blocked_user_id, created_at")
        .eq("blocker_id", user_id).order("created_at", desc=True).execute()
    )
    blocks = response.data or []
    blocked_ids = [block["blocked_user_id"] for block in blocks]
    if not blocked_ids:
        return []
    profiles = (
        get_supabase().table("profiles").select("id, username")
        .in_("id", blocked_ids).execute().data or []
    )
    usernames = {profile["id"]: profile.get("username") for profile in profiles}
    return [{**block, "username": usernames.get(block["blocked_user_id"])} for block in blocks]


def remove_block(user_id: str, blocked_user_id: str) -> None:
    get_supabase().table("user_blocks").delete().eq("blocker_id", user_id).eq(
        "blocked_user_id", blocked_user_id
    ).execute()


def create_report(reporter_id: str, payload: ReportCreate) -> dict[str, object]:
    values = payload.model_dump(exclude_none=True)
    reported_user_id = _validate_and_resolve_report_subject(reporter_id, payload)
    if reported_user_id == reporter_id:
        raise HTTPException(status_code=400, detail="Du kannst deine eigenen Inhalte nicht melden.")
    values["reporter_id"] = reporter_id
    values["reported_user_id"] = reported_user_id
    values["priority"] = "urgent" if payload.reason in {"fraud", "stolen_vehicle"} else "normal"
    response = get_supabase().table("content_reports").insert(values).execute()
    return response.data[0]


def list_moderation_decisions(user_id: str) -> list[dict[str, object]]:
    reports = (
        get_supabase().table("content_reports").select(
            "id, subject_type, vehicle_type, listing_id, reason, status, decision, reviewed_at"
        ).eq("reported_user_id", user_id).eq("status", "resolved")
        .order("reviewed_at", desc=True).execute().data or []
    )
    if not reports:
        return []
    appeals = (
        get_supabase().table("moderation_appeals").select("report_id, status, decision")
        .eq("appellant_id", user_id).in_("report_id", [report["id"] for report in reports]).execute().data or []
    )
    appeals_by_report = {appeal["report_id"]: appeal for appeal in appeals}
    return [{**report, "appeal": appeals_by_report.get(report["id"])} for report in reports]


def create_appeal(user_id: str, report_id: str, statement: str) -> dict[str, object]:
    report = (
        get_supabase().table("content_reports").select("id, reported_user_id, status")
        .eq("id", report_id).limit(1).execute()
    )
    if not report.data or report.data[0].get("reported_user_id") != user_id:
        raise HTTPException(status_code=404, detail="Moderationsentscheidung nicht gefunden.")
    if report.data[0].get("status") not in {"resolved", "rejected"}:
        raise HTTPException(status_code=409, detail="Diese Entscheidung ist noch nicht abgeschlossen.")
    try:
        response = get_supabase().table("moderation_appeals").insert({
            "report_id": report_id,
            "appellant_id": user_id,
            "statement": statement.strip(),
        }).execute()
    except Exception as exc:
        if "23505" in str(exc):
            raise HTTPException(status_code=409, detail="Für diese Entscheidung besteht bereits ein Einspruch.") from exc
        raise
    return response.data[0]


def _validate_and_resolve_report_subject(reporter_id: str, payload: ReportCreate) -> str | None:
    if payload.subject_type == "listing":
        check_vehicle_type(payload.vehicle_type or "")
        response = (
            get_supabase().table(payload.vehicle_type).select("profile_id")
            .eq("id", payload.listing_id).limit(1).execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Inserat nicht gefunden.")
        return response.data[0]["profile_id"]
    if payload.subject_type == "message":
        response = (
            get_supabase().table("messages").select("conversation_id, sender_id")
            .eq("id", payload.message_id).limit(1).execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Nachricht nicht gefunden.")
        message = response.data[0]
        get_participating_conversation(message["conversation_id"], reporter_id)
        return message.get("sender_id")
    response = (
        get_supabase().table("profiles").select("id")
        .eq("id", payload.reported_user_id).limit(1).execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Nutzer nicht gefunden.")
    return payload.reported_user_id
