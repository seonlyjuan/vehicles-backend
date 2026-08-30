from fastapi import HTTPException

from app.db.supabase import get_supabase
from app.moderation.audit import record_action, utc_now
from app.moderation.schemas import ReportDecision
from app.notifications.service import create_notification


def list_reports(status: str | None, page: int, per_page: int) -> dict[str, object]:
    start = (page - 1) * per_page
    query = get_supabase().table("content_reports").select("*", count="exact")
    if status:
        query = query.eq("status", status)
    response = query.order("created_at").range(start, start + per_page - 1).execute()
    items = response.data or []
    _add_report_usernames(items)
    total = response.count or 0
    return {"items": items, "page": page, "per_page": per_page, "total": total}


def decide_report(report_id: str, moderator_id: str, payload: ReportDecision) -> dict[str, object]:
    response = get_supabase().table("content_reports").select("*").eq("id", report_id).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Meldung nicht gefunden.")
    report = response.data[0]
    if report.get("status") in {"resolved", "rejected"}:
        raise HTTPException(status_code=409, detail="Diese Meldung wurde bereits abgeschlossen.")

    if payload.action == "suspend_listing":
        _suspend_listing(report, moderator_id, payload.decision)
    elif payload.action == "suspend_user":
        _suspend_user(report, moderator_id, payload.decision)

    now = utc_now()
    updated = get_supabase().table("content_reports").update({
        "status": payload.outcome,
        "moderator_id": moderator_id,
        "decision": payload.decision,
        "reviewed_at": now,
    }).eq("id", report_id).execute()
    record_action(moderator_id, "decide_report", "report", report_id, payload.decision, {
        "outcome": payload.outcome,
        "action": payload.action,
    })
    if report.get("reported_user_id"):
        create_notification(
            str(report["reported_user_id"]),
            "moderation",
            "Moderationsentscheidung",
            payload.decision,
            f"moderation-report:{report_id}:{payload.outcome}",
            "/profile/settings",
        )
    return updated.data[0]


def _suspend_listing(report: dict[str, object], actor_id: str, reason: str) -> None:
    if report.get("subject_type") != "listing":
        raise HTTPException(status_code=422, detail="Die Meldung betrifft kein Inserat.")
    current = (
        get_supabase().table(str(report["vehicle_type"])).select("status")
        .eq("id", report["listing_id"]).limit(1).execute()
    )
    response = (
        get_supabase().table(str(report["vehicle_type"])).update({
            "status": "suspended", "suspended_at": utc_now(), "updated_at": utc_now(),
        }).eq("id", report["listing_id"]).execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Inserat nicht gefunden.")
    get_supabase().table("conversations").update({
        "status": "closed", "updated_at": utc_now(),
    }).eq("vehicle_type", report["vehicle_type"]).eq("listing_id", report["listing_id"]).execute()
    record_action(actor_id, "suspend_listing", "listing", str(report["listing_id"]), reason, {
        "vehicle_type": report["vehicle_type"],
        "previous_status": current.data[0].get("status") if current.data else None,
    })


def _suspend_user(report: dict[str, object], actor_id: str, reason: str) -> None:
    user_id = report.get("reported_user_id")
    if not user_id:
        raise HTTPException(status_code=422, detail="Kein gemeldeter Nutzer vorhanden.")
    get_supabase().table("profiles").update({"account_status": "suspended"}).eq("id", user_id).execute()
    record_action(actor_id, "suspend_user", "user", str(user_id), reason, {})


def _add_report_usernames(items: list[dict[str, object]]) -> None:
    user_ids = {
        user_id for item in items
        for user_id in (item.get("reporter_id"), item.get("reported_user_id")) if user_id
    }
    if not user_ids:
        return
    profiles = get_supabase().table("profiles").select("id, username").in_("id", list(user_ids)).execute().data or []
    names = {profile["id"]: profile.get("username") for profile in profiles}
    for item in items:
        item["reporter_username"] = names.get(item.get("reporter_id"))
        item["reported_username"] = names.get(item.get("reported_user_id"))

