"""Application configuration for SAHAYAK."""
import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base Directory: root of the backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseModel):
    APP_NAME: str = "SAHAYAK (सहायक)"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    DEBUG: bool = Field(default_factory=lambda: os.getenv("DEBUG", "true").lower() in ("true", "1", "yes"))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    FRONTEND_URL: str = Field(default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:5173"))
    
    # SQLite async default for local development
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", 
            f"sqlite+aiosqlite:///{BASE_DIR / 'sahayak.db'}"
        )
    )
    
    # Security & Session
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", "sahayak_dev_insecure_secret_key_change_in_production")
    )
    SESSION_EXPIRE_HOURS: int = 24
    
    # AI and Voice Provider selection (defaults to local mock/fallback - no external API key needed)
    LLM_PROVIDER: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    VOICE_PROVIDER: str = Field(default_factory=lambda: os.getenv("VOICE_PROVIDER", "browser_mock"))
    STT_PROVIDER: str = Field(default_factory=lambda: os.getenv("STT_PROVIDER", "mock"))
    TTS_PROVIDER: str = Field(default_factory=lambda: os.getenv("TTS_PROVIDER", "mock"))
    OCR_PROVIDER: str = Field(default_factory=lambda: os.getenv("OCR_PROVIDER", "mock"))
    
    # Audio Upload Limits & Safety Controls
    MAX_VOICE_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    MAX_VOICE_DURATION_SECONDS: int = 60  # 60s maximum audio clip
    MAX_CONVERSATION_TURNS: int = 15  # Loop guard
    
    # Document Intelligence & CSC Package Limits
    MAX_DOCUMENT_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    MAX_DOCUMENT_PAGE_COUNT: int = 10  # Max 10 pages per multi-page document
    MAX_IMAGE_DIMENSION: int = 4000  # Prevent decompression bombs
    DOCUMENTS_TEMP_DIR: Path = BASE_DIR / "temp_documents"
    PACKAGES_TEMP_DIR: Path = BASE_DIR / "temp_packages"

    
    # Optional External API Keys (None required for baseline functionality)
    ANTHROPIC_API_KEY: str | None = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    SARVAM_API_KEY: str | None = Field(default_factory=lambda: os.getenv("SARVAM_API_KEY"))
    BHASHINI_USER_ID: str | None = Field(default_factory=lambda: os.getenv("BHASHINI_USER_ID"))
    BHASHINI_API_KEY: str | None = Field(default_factory=lambda: os.getenv("BHASHINI_API_KEY"))
    BHASHINI_PIPELINE_ID: str | None = Field(default_factory=lambda: os.getenv("BHASHINI_PIPELINE_ID"))


settings = Settings()
