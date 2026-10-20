"""Pydantic schemas for SAHAYAK Voice API and LangGraph interactions."""
from typing import Any, Literal
from pydantic import BaseModel, Field
from app.schemas.eligibility import EligibilityAssessResponse


class VoiceTranscribeRequest(BaseModel):
    """Request for transcribing audio."""
    audio_base64: str | None = None
    audio_mime_type: str = "audio/webm"
    language: str = "hi"


class VoiceTranscribeResponse(BaseModel):
    """Transcription output."""
    transcript: str
    confidence: float
    language: str
    is_mock: bool = False
    duration_seconds: float = 0.0


class VoiceTurnRequest(BaseModel):
    """Citizen turn input in voice assistant conversation."""
    text: str | None = Field(default=None, description="Citizen text statement if typed or pre-transcribed")
    audio_base64: str | None = Field(default=None, description="Raw audio bytes in base64 if voice turn")
    audio_mime_type: str = Field(default="audio/webm", description="MIME type of audio")
    confirmed_by_user: bool | None = Field(default=None, description="Explicit confirmation of proposed changes")
    request_tts: bool = Field(default=True, description="Whether to generate TTS audio in response")
    preferred_language: str = Field(default="hi", description="Preferred response language ('hi' or 'en')")


class VoiceTurnResponse(BaseModel):
    """Assistant turn output from LangGraph orchestration."""
    session_id: str
    citizen_id: str
    turn_count: int
    status: Literal["ready", "awaiting_consent", "needs_confirmation", "needs_follow_up", "completed", "error"]
    
    # Transcription & Intent
    transcript: str | None = None
    transcript_confidence: float = 1.0
    intent: str | None = None
    
    # Profile State
    proposed_profile_updates: dict[str, Any] = Field(default_factory=dict)
    persisted_profile_updates: dict[str, Any] = Field(default_factory=dict)
    is_profile_confirmed: bool = False
    
    # Follow-up Question (at most one)
    follow_up_field: str | None = None
    follow_up_question_hi: str | None = None
    follow_up_question_en: str | None = None
    
    # Scheme Evaluations (from Deterministic Engine)
    evaluated_schemes: list[EligibilityAssessResponse] = Field(default_factory=list)
    
    # Spoken & Visual Text Output
    response_text_hi: str
    response_text_en: str
    audio_base64: str | None = None
    audio_format: str = "audio/wav"
    browser_tts_recommended: bool = True
    
    # Provider transparency
    provider_info: dict[str, str] = Field(default_factory=dict)
    error_message: str | None = None


class VoiceSpeakRequest(BaseModel):
    """Request to synthesize audio speech from text."""
    text: str
    language: str = "hi"


class VoiceSpeakResponse(BaseModel):
    """Speech synthesis response."""
    audio_base64: str | None = None
    audio_format: str = "audio/wav"
    spoken_text: str
    is_mock: bool = False
    browser_tts_recommended: bool = True


class VoiceProvidersInfoResponse(BaseModel):
    """Capability information about active voice and AI providers."""
    stt_provider: str
    tts_provider: str
    llm_provider: str
    is_mock: bool
    supported_languages: list[str] = ["hi", "en"]
    audio_limits: dict[str, Any]
