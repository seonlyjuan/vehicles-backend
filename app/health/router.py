from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.health.service import dependency_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_class=JSONResponse)
def readiness_check() -> JSONResponse:
    checks = dependency_status()
    ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ok" if ready else "unavailable", "checks": checks},
        headers={"Cache-Control": "no-store"},
    )
