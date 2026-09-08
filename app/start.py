"""Production entry point: python -m app.start (also works outside Docker)."""

import os

import uvicorn

from app.core.config import settings


def server_options() -> dict[str, object]:
    try:
        port = int(os.getenv("PORT", "8000"))
        workers = int(os.getenv("WEB_CONCURRENCY", "1"))
    except ValueError as exc:
        raise ValueError("PORT and WEB_CONCURRENCY must be integers.") from exc
    if not 1 <= port <= 65535 or workers < 1:
        raise ValueError("PORT must be 1–65535 and WEB_CONCURRENCY at least 1.")
    if workers > 1 and not settings.redis_url:
        raise ValueError("Multiple API workers require REDIS_URL for shared rate limits.")
    return {
        "host": "0.0.0.0",
        "port": port,
        "workers": workers,
        "proxy_headers": True,
        "forwarded_allow_ips": os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
        "timeout_graceful_shutdown": 30,
    }


def main() -> None:
    uvicorn.run("app.main:app", **server_options())


if __name__ == "__main__":
    main()
