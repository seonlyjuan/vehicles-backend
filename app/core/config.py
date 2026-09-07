import os
from dataclasses import dataclass
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    client_origin: str = os.getenv("CLIENT_ORIGIN", "http://localhost:5173")
    client_origin_regex: str | None = os.getenv("CLIENT_ORIGIN_REGEX") or (
        None if os.getenv("APP_ENV", "development").lower() == "production"
        else r"^http://(localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}):5173$"
    )
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    payment_placeholder_enabled: bool = os.getenv("PAYMENT_PLACEHOLDER_ENABLED", "true").lower() == "true"
    listing_fee_chf: Decimal = Decimal(os.getenv("LISTING_FEE_CHF", "0"))
    listing_fee_includes_vat: bool = os.getenv("LISTING_FEE_INCLUDES_VAT", "true").lower() == "true"
    vat_rate_percent: Decimal = Decimal(os.getenv("VAT_RATE_PERCENT", "8.1"))
    payment_webhook_secret: str | None = os.getenv("PAYMENT_WEBHOOK_SECRET")
    payment_webhook_tolerance_seconds: int = int(os.getenv("PAYMENT_WEBHOOK_TOLERANCE_SECONDS", "300"))
    refund_window_days: int = int(os.getenv("REFUND_WINDOW_DAYS", "14"))
    listing_duration_days: int = int(os.getenv("LISTING_DURATION_DAYS", "30"))
    redis_url: str | None = os.getenv("REDIS_URL")
    enforce_https: bool = os.getenv(
        "ENFORCE_HTTPS",
        "true" if os.getenv("APP_ENV", "development").lower() == "production" else "false",
    ).lower() == "true"
    allowed_hosts: tuple[str, ...] = tuple(
        host.strip() for host in os.getenv(
            "ALLOWED_HOSTS",
            "localhost,127.0.0.1" if os.getenv("APP_ENV", "development").lower() == "production" else "*",
        ).split(",") if host.strip()
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()
