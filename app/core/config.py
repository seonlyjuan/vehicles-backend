import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")
    client_origin: str = os.getenv("CLIENT_ORIGIN", "http://localhost:5173")
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")


settings = Settings()
