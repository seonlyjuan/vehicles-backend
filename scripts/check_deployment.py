"""Read-only checks for core schema, postal codes and the private image bucket."""

import json

from app.db.supabase import get_supabase


def check_deployment() -> dict[str, str]:
    database = get_supabase()
    results = {}
    for table in (
        "profiles", "cars", "motorbikes", "bicycles", "vehicle_images",
        "conversations", "messages", "message_notifications", "user_notifications",
        "user_blocks", "content_reports", "moderation_actions",
    ):
        try:
            database.table(table).select("id").limit(1).execute()
            results[table] = "ok"
        except Exception:
            results[table] = "unavailable"
    try:
        rows = database.table("swiss_postal_codes").select("postal_code").limit(1).execute().data
        results["swiss_postal_codes"] = "ok" if rows else "empty: import required"
    except Exception:
        results["swiss_postal_codes"] = "unavailable"
    try:
        bucket = database.storage.get_bucket("vehicles-images")
        results["vehicles-images"] = "ok" if bucket.public is False else "must be private"
    except Exception:
        results["vehicles-images"] = "unavailable"
    return results


def main() -> None:
    results = check_deployment()
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if all(value == "ok" for value in results.values()) else 1)


if __name__ == "__main__":
    main()
