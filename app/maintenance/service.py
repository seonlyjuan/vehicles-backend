from datetime import datetime, timedelta, timezone

from app.db.supabase import get_supabase
from app.notifications.service import create_notification
from app.vehicles.constants import VALID_TYPES
from app.vehicles.storage_service import remove_vehicle_files

DELETED_LISTING_RETENTION_DAYS = 30
CLOSED_CONVERSATION_RETENTION_DAYS = 365
READ_NOTIFICATION_RETENTION_DAYS = 90
RESOLVED_REPORT_RETENTION_DAYS = 3 * 365
MODERATION_AUDIT_RETENTION_DAYS = 3 * 365
PAYMENT_RECORD_RETENTION_DAYS = 10 * 365 + 3


def run_retention_cleanup(now: datetime | None = None) -> dict[str, int]:
    current = now or datetime.now(timezone.utc)
    result = {
        "expired_listings": 0,
        "expiry_reminders": 0,
        "purged_listings": 0,
        "purged_conversations": 0,
        "purged_notifications": 0,
        "purged_platform_notifications": 0,
        "purged_reports": 0,
        "purged_moderation_actions": 0,
        "purged_payment_records": 0,
    }
    supabase = get_supabase()

    for vehicle_type in VALID_TYPES:
        reminder_limit = current + timedelta(days=3)
        expiring = (
            supabase.table(vehicle_type).select("id, profile_id, title, expires_at")
            .eq("status", "active").gte("expires_at", current.isoformat())
            .lte("expires_at", reminder_limit.isoformat()).execute().data or []
        )
        for listing in expiring:
            create_notification(
                str(listing["profile_id"]),
                "listing_expiring",
                "Inserat läuft bald ab",
                f"Dein Inserat „{listing['title']}“ läuft in weniger als drei Tagen ab.",
                f"listing-expiring:{vehicle_type}:{listing['id']}:{listing['expires_at']}",
                f"/vehicles/{vehicle_type}/listing/{listing['id']}",
            )
        result["expiry_reminders"] += len(expiring)

        expired = (
            supabase.table(vehicle_type).update({"status": "expired", "updated_at": current.isoformat()})
            .eq("status", "active").lte("expires_at", current.isoformat()).execute()
        )
        result["expired_listings"] += len(expired.data or [])
        for listing in expired.data or []:
            create_notification(
                str(listing["profile_id"]),
                "listing_expired",
                "Inserat abgelaufen",
                f"Dein Inserat „{listing['title']}“ ist nicht mehr öffentlich sichtbar.",
                f"listing-expired:{vehicle_type}:{listing['id']}",
                "/profile/listings",
            )

        cutoff = current - timedelta(days=DELETED_LISTING_RETENTION_DAYS)
        deleted = (
            supabase.table(vehicle_type).select("id")
            .eq("status", "deleted").lte("deleted_at", cutoff.isoformat()).execute().data or []
        )
        for item in deleted:
            _purge_listing_images(vehicle_type, item["id"])
            supabase.table(vehicle_type).delete().eq("id", item["id"]).execute()
        result["purged_listings"] += len(deleted)

    conversation_cutoff = current - timedelta(days=CLOSED_CONVERSATION_RETENTION_DAYS)
    conversations = (
        supabase.table("conversations").delete().eq("status", "closed")
        .lte("updated_at", conversation_cutoff.isoformat()).execute()
    )
    result["purged_conversations"] = len(conversations.data or [])

    notification_cutoff = current - timedelta(days=READ_NOTIFICATION_RETENTION_DAYS)
    notifications = (
        supabase.table("message_notifications").delete().not_.is_("read_at", "null")
        .lte("read_at", notification_cutoff.isoformat()).execute()
    )
    result["purged_notifications"] = len(notifications.data or [])

    platform_notifications = (
        supabase.table("user_notifications").delete().not_.is_("read_at", "null")
        .lte("read_at", notification_cutoff.isoformat()).execute()
    )
    result["purged_platform_notifications"] = len(platform_notifications.data or [])

    report_cutoff = current - timedelta(days=RESOLVED_REPORT_RETENTION_DAYS)
    reports = (
        supabase.table("content_reports").delete().in_("status", ["resolved", "rejected"])
        .lte("reviewed_at", report_cutoff.isoformat()).execute()
    )
    result["purged_reports"] = len(reports.data or [])

    audit_cutoff = current - timedelta(days=MODERATION_AUDIT_RETENTION_DAYS)
    actions = (
        supabase.table("moderation_actions").delete()
        .lte("created_at", audit_cutoff.isoformat()).execute()
    )
    result["purged_moderation_actions"] = len(actions.data or [])

    payment_cutoff = current - timedelta(days=PAYMENT_RECORD_RETENTION_DAYS)
    payments = (
        supabase.table("listing_payments").delete()
        .lte("created_at", payment_cutoff.isoformat()).execute()
    )
    result["purged_payment_records"] = len(payments.data or [])
    return result


def _purge_listing_images(vehicle_type: str, listing_id: str) -> None:
    supabase = get_supabase()
    images = (
        supabase.table("vehicle_images").select("storage_path")
        .eq("vehicle_type", vehicle_type).eq("vehicle_id", listing_id).execute().data or []
    )
    paths = [image["storage_path"] for image in images]
    if paths:
        remove_vehicle_files(paths)
    supabase.table("vehicle_images").delete().eq("vehicle_type", vehicle_type).eq(
        "vehicle_id", listing_id
    ).execute()
