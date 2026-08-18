from functools import lru_cache

from fastapi import HTTPException
from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(status_code=500, detail="Supabase ist noch nicht konfiguriert.")
    return create_client(settings.supabase_url, settings.supabase_key)
