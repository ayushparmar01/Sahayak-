"""Health response schemas."""
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    version: str
    environment: str
    database_connected: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
