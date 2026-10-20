"""Main FastAPI application entrypoint for SAHAYAK."""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import init_db
from app.api.api_v1 import api_router
from app.services.ocr.cleanup import cleanup_stale_temp_files


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to handle startup and shutdown."""
    # Ensure database tables exist
    await init_db()
    # Clean up any leftover temporary files from prior ungraceful terminations
    cleanup_stale_temp_files(max_age_seconds=3600)
    yield
    # Graceful shutdown tasks
    cleanup_stale_temp_files(max_age_seconds=0)



app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Voice-First Multi-Agent AI for Government Scheme Access (Deviathon 2.0)",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        settings.FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "स्वागत है — SAHAYAK (सहायक) API सेवा सक्रिय है",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Disabled in production",
    }
