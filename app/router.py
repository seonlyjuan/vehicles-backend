from fastapi import APIRouter

from app.health.router import router as health_router
from app.profiles.router import router as profile_router
from app.vehicles.router import router as vehicles_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(profile_router)
api_router.include_router(vehicles_router)
