"""V1 API Router aggregating all sub-routes."""
from fastapi import APIRouter

from app.api.endpoints.health import router as health_router
from app.api.endpoints.sessions import router as sessions_router
from app.api.endpoints.schemes import router as schemes_router
from app.api.endpoints.profile import router as profile_router
from app.api.endpoints.eligibility import router as eligibility_router
from app.api.endpoints.voice import router as voice_router
from app.api.endpoints.documents import router as documents_router
from app.api.endpoints.applications import router as applications_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(schemes_router)
api_router.include_router(profile_router)
api_router.include_router(eligibility_router)
api_router.include_router(voice_router)
api_router.include_router(documents_router)
api_router.include_router(applications_router)


