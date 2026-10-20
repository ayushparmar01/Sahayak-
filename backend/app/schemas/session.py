"""Session management schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class SessionInitRequest(BaseModel):
    preferred_language: str = Field(default="hi", pattern="^(hi|en)$")
    consent_given: bool = Field(default=False)


class SessionInitResponse(BaseModel):
    session_id: str
    citizen_id: str
    preferred_language: str
    consent_granted_at: datetime | None = None
    status: str = "active"
    message: str


class SessionTerminateRequest(BaseModel):
    session_id: str


class SessionTerminateResponse(BaseModel):
    session_id: str
    status: str = "terminated"
    message: str
    data_purged: bool = True
