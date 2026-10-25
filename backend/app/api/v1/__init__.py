"""Version 1 API router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    assistant,
    auth,
    consents,
    drafts,
    health,
    postal,
    privacy,
    profile,
    schemes,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(consents.router)
api_router.include_router(postal.router)
api_router.include_router(schemes.router)
api_router.include_router(assistant.router)
api_router.include_router(drafts.router)
api_router.include_router(privacy.router)
api_router.include_router(admin.router)
