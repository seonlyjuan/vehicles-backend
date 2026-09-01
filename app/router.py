from fastapi import APIRouter

from app.health.router import router as health_router
from app.profiles.router import router as profile_router
from app.vehicles.router import router as vehicles_router
from app.messages.router import router as messages_router
from app.locations.router import router as locations_router
from app.legal.router import router as legal_router
from app.safety.router import router as safety_router
from app.moderation.router import router as moderation_router
from app.notifications.router import router as notifications_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(profile_router)
api_router.include_router(vehicles_router)
api_router.include_router(messages_router)
api_router.include_router(locations_router)
api_router.include_router(legal_router)
api_router.include_router(safety_router)
api_router.include_router(moderation_router)
api_router.include_router(notifications_router)
