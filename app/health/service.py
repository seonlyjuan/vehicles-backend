"""Read-only dependency checks. No user data or credentials leave this module."""

from functools import lru_cache

from redis import Redis
from supabase import Client, ClientOptions, create_client

from app.core.config import settings


@lru_cache
def _readiness_supabase() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("Supabase is not configured.")
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
        options=ClientOptions(
            postgrest_client_timeout=5, auto_refresh_token=False, persist_session=False,
        ),
    )


@lru_cache
def _readiness_redis() -> Redis:
    return Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


def dependency_status() -> dict[str, str]:
    checks = {}
    try:
        _readiness_supabase().table("profiles").select("id").limit(1).execute()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
    if settings.redis_url:
        try:
            _readiness_redis().ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
    return checks
