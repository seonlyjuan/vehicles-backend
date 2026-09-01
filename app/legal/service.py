from fastapi import HTTPException

from app.core.config import settings
from app.db.supabase import get_supabase
from app.legal.constants import (
    CURRENT_TERMS_SHA256,
    CURRENT_TERMS_VERSION,
    LISTING_PUBLICATION_CONTEXT,
    TERMS_DOCUMENT_TYPE,
    TERMS_LANGUAGE,
)


def get_current_terms() -> dict[str, object]:
    response = (
        get_supabase().table("legal_documents")
        .select("id, version, display_version, title, public_path, content_sha256, status, effective_from")
        .eq("document_type", TERMS_DOCUMENT_TYPE)
        .eq("version", CURRENT_TERMS_VERSION)
        .eq("language", TERMS_LANGUAGE)
        .eq("content_sha256", CURRENT_TERMS_SHA256)
        .limit(1).execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=503,
            detail="Die aktuelle AGB-Version ist in der Datenbank nicht konfiguriert.",
        )

    document = response.data[0]
    if settings.is_production and document.get("status") != "published":
        raise HTTPException(
            status_code=503,
            detail="Die AGB sind noch nicht für den produktiven Betrieb freigegeben.",
        )
    return document


def record_listing_terms_acceptance(
    user_id: str,
    vehicle_type: str,
    listing_id: str,
    accepted_version: str,
) -> dict[str, object]:
    document = get_current_terms()
    if accepted_version != document["version"]:
        raise HTTPException(
            status_code=409,
            detail="Die AGB wurden zwischenzeitlich aktualisiert. Bitte lies und bestätige die aktuelle Version.",
        )

    supabase = get_supabase()
    existing = _find_acceptance(
        user_id,
        str(document["id"]),
        vehicle_type,
        listing_id,
    )
    if existing:
        return existing

    values = {
        "user_id": user_id,
        "document_id": document["id"],
        "document_version": document["version"],
        "document_sha256": document["content_sha256"],
        "context": LISTING_PUBLICATION_CONTEXT,
        "vehicle_type": vehicle_type,
        "listing_id": listing_id,
    }
    try:
        response = supabase.table("legal_acceptances").insert(values).execute()
        return response.data[0]
    except Exception:
        # A parallel retry may have inserted the same immutable acceptance.
        existing = _find_acceptance(
            user_id,
            str(document["id"]),
            vehicle_type,
            listing_id,
        )
        if existing:
            return existing
        raise


def _find_acceptance(
    user_id: str,
    document_id: str,
    vehicle_type: str,
    listing_id: str,
) -> dict[str, object] | None:
    response = (
        get_supabase().table("legal_acceptances").select("*")
        .eq("user_id", user_id)
        .eq("document_id", document_id)
        .eq("context", LISTING_PUBLICATION_CONTEXT)
        .eq("vehicle_type", vehicle_type)
        .eq("listing_id", listing_id)
        .limit(1).execute()
    )
    return response.data[0] if response.data else None
