from fastapi import HTTPException

from app.db.supabase import get_supabase


def search_swiss_locations(query: str) -> list[dict[str, str]]:
    normalized = query.strip()
    if len(normalized) < 2:
        return []

    table = get_supabase().table("swiss_postal_codes").select("postal_code, locality, canton")
    if normalized.isdigit():
        table = table.like("postal_code", f"{normalized}%")
    else:
        table = table.ilike("locality", f"{normalized}%")
    response = table.order("postal_code").order("locality").limit(20).execute()
    return response.data or []


def validate_swiss_location(postal_code: str, locality: str, canton: str) -> dict[str, str]:
    response = (
        get_supabase()
        .table("swiss_postal_codes")
        .select("postal_code, locality, canton")
        .eq("postal_code", postal_code.strip())
        .ilike("locality", locality.strip())
        .eq("canton", canton.strip().upper())
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=422,
            detail="Die Kombination aus Schweizer PLZ, Ort und Kanton ist ungültig.",
        )
    return response.data[0]

