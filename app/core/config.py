import os
from dataclasses import dataclass
from decimal import Decimal
from ipaddress import ip_address
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()


def _public_https_url(value: str | None, *, origin_only: bool = False) -> bool:
    try:
        parsed = urlsplit(value or "")
        host = parsed.hostname or ""
        if (
            parsed.scheme != "https" or not host or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.port not in (None, 443)
            or (origin_only and parsed.path not in ("", "/"))
            or host == "localhost" or host.endswith((".localhost", ".local"))
        ):
            return False
        try:
            return ip_address(host).is_global
        except ValueError:
            return "." in host and not any(character.isspace() for character in host)
    except ValueError:
        return False


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

    def __post_init__(self) -> None:
        if self.environment.lower() not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test or production.")
        if not self.is_production:
            return

        errors = []
        if not _public_https_url(self.client_origin, origin_only=True) or self.client_origin.endswith("/"):
            errors.append("CLIENT_ORIGIN must be a public HTTPS origin without a trailing slash")
        if self.client_origin_regex:
            errors.append("CLIENT_ORIGIN_REGEX must be unset in production")
        if not _public_https_url(self.supabase_url, origin_only=True):
            errors.append("SUPABASE_URL must be a public HTTPS URL")
        if not self.supabase_service_role_key or self.supabase_service_role_key.startswith(("your-", "replace-")):
            errors.append("SUPABASE_SERVICE_ROLE_KEY must be configured with a server-only key")
        if not self.allowed_hosts or any(
            not _public_https_url(f"https://{host}", origin_only=True)
            or any(character in host for character in "*/:@?#")
            for host in self.allowed_hosts
        ):
            errors.append("ALLOWED_HOSTS must contain explicit public API hostnames without a scheme or port")
        if not self.enforce_https:
            errors.append("ENFORCE_HTTPS must be true in production")
        if self.redis_url:
            try:
                parsed = urlsplit(self.redis_url)
                valid_redis = parsed.scheme in {"redis", "rediss"} and bool(parsed.hostname)
                parsed.port
            except ValueError:
                valid_redis = False
            if not valid_redis:
                errors.append("REDIS_URL must be a valid redis:// or rediss:// URL")
        if errors:
            # Report variable names only; never include configured credentials.
            raise ValueError("Invalid production configuration: " + "; ".join(errors))


settings = Settings()
